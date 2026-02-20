## ADDED Requirements

### Requirement: Markdown Export
The system SHALL export a complete book or individual chapters as Markdown (.md) files with proper heading hierarchy (# Book Title, ## Chapter Title, ### Scene Title).

#### Scenario: Export full book as Markdown
- **WHEN** user clicks Export Markdown for a book
- **THEN** a .md file is downloaded containing all chapters and scenes in order with proper headings

### Requirement: Plain Text Export
The system SHALL export a complete book or individual chapters as plain text (.txt) files.

#### Scenario: Export single chapter as TXT
- **WHEN** user clicks Export TXT for a specific chapter
- **THEN** a .txt file is downloaded containing all scenes of that chapter concatenated with scene breaks
