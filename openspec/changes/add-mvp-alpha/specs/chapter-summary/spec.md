## ADDED Requirements

### Requirement: Auto Chapter Summary
The system SHALL automatically generate a chapter summary when the user marks a chapter as done (chapter_mark_done event).
The summary SHALL include: 1-2 paragraph narrative summary, key events list, keywords, entities, and plot_threads references.

#### Scenario: Summary generated on chapter completion
- **WHEN** user marks chapter as done
- **THEN** a chapter_summary record is created with summary_md, keywords_json, entities_json, and plot_threads_json

#### Scenario: Summary injected in next chapter context
- **WHEN** generating content for the next chapter
- **THEN** the previous chapter's summary is included in the long-term memory layer of the Context Pack
