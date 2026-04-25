# UI Vocabulary — Layer 1 Static Reference

This vocabulary is always injected into every test case generation request.
It defines shared UI interaction patterns and save behaviors used across all forms.

## Save Behavior Enums

- `SAVE_EXPLICIT` — user must explicitly click a save button/icon; data not persisted until save action
- `SAVE_ON_BLUR` — field value is persisted when focus leaves the field (blur event)
- `SAVE_ON_SUBMIT` — entire form saved on form submit action
- `SAVE_AUTO` — data is auto-saved without user action (e.g. debounced on change)

## Save Trigger Patterns

Save triggers define the exact UI action that initiates a save operation.

Examples:
- `"click → [data-testid="save-icon"]"` — click on element with data-testid attribute
- `"click → button[type='submit']"` — click submit button
- `"blur → input[name='field_name']"` — focus leaving a specific input
- `"keydown → Enter"` — pressing Enter key

## Validation Timing Enums

- `VALIDATE_ON_SAVE` — validation errors appear only after save is attempted
- `VALIDATE_ON_BLUR` — validation errors appear when field loses focus
- `VALIDATE_ON_CHANGE` — validation errors appear as user types

## Blur Event Definition

A **blur event** occurs when a UI element loses keyboard focus. This happens when:
- User clicks outside the element
- User presses Tab to move to next element
- User presses Escape (in some implementations)
- A calendar/date picker overlay closes

## Button States

- **enabled** — button is interactive; click triggers action
- **disabled** — button is visually present but not clickable (greyed out)
- **loading** — button shows spinner/progress; action is in progress; further clicks blocked

## Toast Notification Patterns

- **success toast** — green notification confirming successful operation
- **error toast** — red notification indicating failure
- **warning toast** — amber notification for non-blocking issues

Toast notifications typically auto-dismiss after 3–5 seconds.

## Error State Descriptors

- **field validation error** — inline error message below a form field
- **form-level error** — error summary at top or bottom of form
- **service error** — error from backend (network/server failure)
- **required field error** — appears when a required field is empty on save attempt

## Field Interaction Steps

Standard steps for interacting with common field types:

**Text input**:
1. Click the field to focus it
2. Type the value
3. Move focus away (Tab/click outside) to trigger blur

**Dropdown/Select**:
1. Click the dropdown to open it
2. Click the desired option
3. Dropdown closes; selected value shown

**Date picker**:
1. Click the date field to open calendar overlay
2. Select date by clicking, or type in DD/MM/YYYY format
3. Calendar closes automatically; field value is set
4. Blur is triggered after calendar closes

**Checkbox**:
1. Click the checkbox to toggle its state
2. State changes immediately (checked/unchecked)

**File upload**:
1. Click the upload button/zone
2. Select file from OS dialog
3. File appears in upload list

## Blur-Does-Not-Save Pattern

When a form has `save_behavior: SAVE_EXPLICIT`, blurring a field does **not** save data.
Test cases must verify that data is NOT persisted on blur — only on explicit save trigger.

## Blur-Triggers-Save Pattern

When a field has `save_on_blur: true`, blurring that field **does** trigger a save.
Test cases must verify that blur on that specific field causes data persistence.
