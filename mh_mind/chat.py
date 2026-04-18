"""Citation-aware chat: retrieve context, prompt the LLM, parse citations."""

import re
from dataclasses import dataclass, field

from mh_mind.llm import Message, get_provider
from mh_mind.retrieve import retrieve

SYSTEM_PROMPT = """\
You are mh-mind, a personal research assistant. The user is chatting with their \
own corpus of Apple Notes and Word documents.

You will be given numbered context excerpts from the user's corpus. Use them to \
answer the user's question. Follow these rules strictly:

1. **Cite every claim** using inline references like [1], [2], etc. Each number \
corresponds to the context excerpt with that number.
2. Only cite excerpt numbers that were actually provided. Never invent citations.
3. If the provided excerpts don't contain enough information, say so honestly \
rather than guessing.
4. Synthesise across multiple excerpts when relevant — don't just summarise one.
5. Write in a clear, direct style. The user is an academic.
"""


@dataclass
class Source:
    number: int
    text: str
    source: str  # "notes" or "docs"
    source_id: str
    metadata: dict


@dataclass
class ChatResponse:
    answer: str
    sources: list[Source] = field(default_factory=list)


def _build_context_block(results: list[dict]) -> tuple[str, list[Source]]:
    """Format retrieved chunks as numbered excerpts and build Source objects."""
    lines = []
    sources = []

    for i, r in enumerate(results, 1):
        meta = r["metadata"]
        title = meta.get("title", "Untitled")
        date = meta.get("created", meta.get("modified", ""))
        source_label = "Apple Note" if r["source"] == "notes" else "Word doc"

        lines.append(f"[{i}] ({source_label}: \"{title}\", {date})")
        lines.append(r["text"])
        lines.append("")

        sources.append(Source(
            number=i,
            text=r["text"],
            source=r["source"],
            source_id=r["source_id"],
            metadata=meta,
        ))

    return "\n".join(lines), sources


def _validate_citations(answer: str, max_citation: int) -> str:
    """Remove or flag citation numbers that don't correspond to a provided excerpt."""
    def replace_invalid(match: re.Match) -> str:
        n = int(match.group(1))
        if 1 <= n <= max_citation:
            return match.group(0)
        return f"[?{n}]"  # flag invalid citations visually

    return re.sub(r"\[(\d+)\]", replace_invalid, answer)


def answer(
    query: str,
    scope: str = "both",
    conversation_history: list[Message] | None = None,
    top_k: int = 10,
    temperature: float = 0.3,
) -> ChatResponse:
    """Answer a query using retrieved context and the LLM.

    Args:
        query: The user's question.
        scope: "notes", "docs", or "both".
        conversation_history: Prior messages in the session (for multi-turn).
        top_k: Number of context chunks to retrieve.
        temperature: LLM sampling temperature (0.0=precise, 2.0=very creative).

    Returns:
        ChatResponse with the answer and source list.
    """
    # Retrieve relevant chunks
    results = retrieve(query, scope=scope, top_k=top_k)

    if not results:
        return ChatResponse(
            answer="I couldn't find any relevant content in your corpus for this query. "
                   "Try broadening your question or checking that your notes have been synced.",
            sources=[],
        )

    context_block, sources = _build_context_block(results)

    # Build the message list
    messages: list[Message] = [Message(role="system", content=SYSTEM_PROMPT)]

    # Include conversation history if provided
    if conversation_history:
        messages.extend(conversation_history)

    # Add the user's query with context
    user_message = f"""Here are relevant excerpts from your corpus:

{context_block}

Question: {query}"""

    messages.append(Message(role="user", content=user_message))

    # Call the LLM
    provider = get_provider()
    raw_answer = provider.complete(messages, temperature=temperature)

    # Validate citations
    validated_answer = _validate_citations(raw_answer, len(sources))

    return ChatResponse(answer=validated_answer, sources=sources)
