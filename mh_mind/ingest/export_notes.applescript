-- export_notes.applescript
-- Exports all Apple Notes as Markdown files with YAML frontmatter.
-- Each note becomes ~/mh-mind/notes_export/<folder>/<note-id>.md
--
-- Usage: osascript export_notes.applescript [output_dir]
-- Default output_dir: ~/mh-mind/notes_export

on run argv
	-- Output directory (allow override for testing)
	if (count of argv) > 0 then
		set outputRoot to item 1 of argv
	else
		set outputRoot to (POSIX path of (path to home folder)) & "mh-mind/notes_export"
	end if

	-- Ensure output root exists
	do shell script "mkdir -p " & quoted form of outputRoot

	set noteCount to 0
	set errorCount to 0

	tell application "Notes"
		set allAccounts to every account
		repeat with acct in allAccounts
			set allFolders to every folder of acct
			repeat with f in allFolders
				set folderName to name of f
				-- Sanitise folder name for filesystem
				set safeFolderName to my sanitiseFilename(folderName)
				set folderPath to outputRoot & "/" & safeFolderName
				do shell script "mkdir -p " & quoted form of folderPath

				set allNotes to every note of f
				repeat with n in allNotes
					try
						set noteId to id of n
						set noteTitle to name of n
						set noteBody to body of n -- HTML content
						set noteCreated to creation date of n
						set noteModified to modification date of n

						-- Format dates as ISO 8601
						set createdStr to my formatDate(noteCreated)
						set modifiedStr to my formatDate(noteModified)

						-- Build a safe filename from the note ID
						-- Apple Notes IDs look like "x-coredata://..." — hash to a short hex string
						set safeId to my hashId(noteId)
						set filePath to folderPath & "/" & safeId & ".md"

						-- Build file content: YAML frontmatter + body
						set fileContent to "---" & linefeed
						set fileContent to fileContent & "title: " & my yamlEscape(noteTitle) & linefeed
						set fileContent to fileContent & "folder: " & my yamlEscape(folderName) & linefeed
						set fileContent to fileContent & "created: " & createdStr & linefeed
						set fileContent to fileContent & "modified: " & modifiedStr & linefeed
						set fileContent to fileContent & "note_id: " & my yamlEscape(noteId) & linefeed
						set fileContent to fileContent & "---" & linefeed & linefeed
						set fileContent to fileContent & noteBody & linefeed

						-- Write the file (overwrites if exists)
						my writeFile(filePath, fileContent)

						set noteCount to noteCount + 1
					on error errMsg
						set errorCount to errorCount + 1
						log "Error exporting note: " & errMsg
					end try
				end repeat
			end repeat
		end repeat
	end tell

	return "exported:" & noteCount & ",errors:" & errorCount
end run

-- Format an AppleScript date as ISO 8601 (YYYY-MM-DDTHH:MM:SS)
on formatDate(d)
	set y to year of d
	set m to my zeroPad(month of d as integer)
	set dy to my zeroPad(day of d)
	set h to my zeroPad(hours of d)
	set mn to my zeroPad(minutes of d)
	set s to my zeroPad(seconds of d)
	return (y as text) & "-" & m & "-" & dy & "T" & h & ":" & mn & ":" & s
end formatDate

on zeroPad(n)
	if n < 10 then
		return "0" & (n as text)
	else
		return n as text
	end if
end zeroPad

-- Escape a string for safe use as a YAML value (wrap in quotes if needed)
on yamlEscape(s)
	set s to s as text
	-- If the string contains colons, quotes, or newlines, wrap in double quotes with escaping
	if s contains ":" or s contains "\"" or s contains linefeed or s contains "#" then
		-- Escape backslashes first, then double quotes, then newlines
		set s to my replaceText(s, "\\", "\\\\")
		set s to my replaceText(s, "\"", "\\\"")
		set s to my replaceText(s, linefeed, "\\n")
		set s to my replaceText(s, return, "\\n")
		return "\"" & s & "\""
	else
		return "\"" & s & "\""
	end if
end yamlEscape

-- Simple text replacement
on replaceText(theText, searchStr, replaceStr)
	set AppleScript's text item delimiters to searchStr
	set theItems to text items of theText
	set AppleScript's text item delimiters to replaceStr
	set theText to theItems as text
	set AppleScript's text item delimiters to ""
	return theText
end replaceText

-- Sanitise a string for use as a filename/directory name
on sanitiseFilename(s)
	set s to my replaceText(s, "/", "_")
	set s to my replaceText(s, ":", "_")
	set s to my replaceText(s, "\"", "_")
	return s
end sanitiseFilename

-- Hash a note ID to a short hex string using md5
on hashId(noteId)
	set hashResult to do shell script "echo -n " & quoted form of (noteId as text) & " | md5 | cut -c1-12"
	return hashResult
end hashId

-- Write text content to a file using AppleScript native I/O
on writeFile(filePath, content)
	set posixFile to POSIX file filePath
	try
		set fileRef to open for access posixFile with write permission
		set eof fileRef to 0
		write content to fileRef as «class utf8»
		close access fileRef
	on error errMsg
		try
			close access posixFile
		end try
		error "Failed to write " & filePath & ": " & errMsg
	end try
end writeFile
