# BDD Test Cases — Leave Request Form

**Story:** Employee submits a new leave request
**Form:** `leave_request_form`
**Author:** QA Engineering

---

## Coverage Summary

| Category | Count |
|---|---|
| Happy path | 5 |
| Negative / validation | 9 |
| Edge cases | 8 |
| Field interactions (blur / focus / save) | 13 |
| **Total scenarios** | **30** |

---

## Background

```gherkin
Background:
  Given the employee is logged into the HR system
  And the employee navigates to "Submit Leave Request"
  And the leave_request_form is displayed with the following fields:
    | Field       | Type     | Required |
    | Leave Type  | Dropdown | Yes      |
    | Start Date  | Date     | Yes      |
    | End Date    | Date     | Yes      |
    | Reason      | Textarea | No       |
  And a "Submit" button is visible
```

---

## Happy Path

### TC-HP-01 · Submit with all fields filled

```gherkin
@happy_path @smoke
Scenario: Employee successfully submits a leave request with all fields filled
  Given the employee selects "Annual Leave" from the Leave Type dropdown
  And the employee sets the Start Date to "2025-08-01"
  And the employee sets the End Date to "2025-08-05"
  And the employee enters "Family vacation" in the Reason field
  When the employee clicks the "Submit" button
  Then the leave request is created with status "Pending Approval"
  And a success notification is displayed: "Your leave request has been submitted successfully"
  And the employee is redirected to the Leave Requests list page
  And the submitted request appears in the list with correct details
```

### TC-HP-02 · Submit without providing a reason (optional field)

```gherkin
@happy_path @smoke
Scenario: Employee successfully submits a leave request without providing a reason
  Given the employee selects "Sick Leave" from the Leave Type dropdown
  And the employee sets the Start Date to "2025-07-10"
  And the employee sets the End Date to "2025-07-10"
  And the Reason field is left empty
  When the employee clicks the "Submit" button
  Then the leave request is created with status "Pending Approval"
  And a success notification is displayed
  And the submitted request shows an empty reason field
```

### TC-HP-03 · Single-day leave request (start date equals end date)

```gherkin
@happy_path
Scenario: Employee submits a single-day leave request (start date equals end date)
  Given the employee selects "Casual Leave" from the Leave Type dropdown
  And the employee sets the Start Date to "2025-09-15"
  And the employee sets the End Date to "2025-09-15"
  When the employee clicks the "Submit" button
  Then the leave request is accepted
  And the duration is calculated as 1 day
  And the status is set to "Pending Approval"
```

### TC-HP-04 · Submit for all available leave types

```gherkin
@happy_path
Scenario Outline: Employee submits a leave request for different leave types
  Given the employee selects "<leave_type>" from the Leave Type dropdown
  And the employee sets the Start Date to "2025-08-01"
  And the employee sets the End Date to "2025-08-03"
  When the employee clicks the "Submit" button
  Then the leave request is created with status "Pending Approval"
  And the leave type is recorded as "<leave_type>"

  Examples:
    | leave_type        |
    | Annual Leave      |
    | Sick Leave        |
    | Casual Leave      |
    | Maternity Leave   |
    | Paternity Leave   |
    | Unpaid Leave      |
    | Bereavement Leave |
```

---

## Negative / Validation Cases

### TC-NV-01 · Submit without selecting a leave type

```gherkin
@negative @validation
Scenario: Employee tries to submit without selecting a leave type
  Given the Leave Type field is empty
  And the employee sets the Start Date to "2025-08-01"
  And the employee sets the End Date to "2025-08-03"
  When the employee clicks the "Submit" button
  Then the form is NOT submitted
  And an inline validation error is shown below Leave Type: "Leave type is required"
  And the Leave Type field is highlighted in red
```

### TC-NV-02 · Submit without a start date

```gherkin
@negative @validation
Scenario: Employee tries to submit without a start date
  Given the employee selects "Annual Leave" from the Leave Type dropdown
  And the Start Date field is left empty
  And the employee sets the End Date to "2025-08-03"
  When the employee clicks the "Submit" button
  Then the form is NOT submitted
  And an inline validation error is shown below Start Date: "Start date is required"
```

### TC-NV-03 · Submit without an end date

```gherkin
@negative @validation
Scenario: Employee tries to submit without an end date
  Given the employee selects "Annual Leave" from the Leave Type dropdown
  And the employee sets the Start Date to "2025-08-01"
  And the End Date field is left empty
  When the employee clicks the "Submit" button
  Then the form is NOT submitted
  And an inline validation error is shown below End Date: "End date is required"
```

### TC-NV-04 · Submit with end date earlier than start date

```gherkin
@negative @validation
Scenario: Employee tries to submit with end date earlier than start date
  Given the employee selects "Annual Leave" from the Leave Type dropdown
  And the employee sets the Start Date to "2025-08-10"
  And the employee sets the End Date to "2025-08-05"
  When the employee clicks the "Submit" button
  Then the form is NOT submitted
  And an inline validation error is shown: "End date cannot be earlier than start date"
  And the End Date field is highlighted in red
```

### TC-NV-05 · Submit with all required fields empty

```gherkin
@negative @validation
Scenario: Employee tries to submit all required fields empty
  Given all form fields are empty
  When the employee clicks the "Submit" button
  Then the form is NOT submitted
  And validation errors are shown for all required fields simultaneously:
    | Field      | Error Message          |
    | Leave Type | Leave type is required |
    | Start Date | Start date is required |
    | End Date   | End date is required   |
```

### TC-NV-06 · Reason field exceeds maximum character limit

```gherkin
@negative @validation
Scenario: Employee enters a Reason exceeding the maximum character limit
  Given the employee selects "Annual Leave" from the Leave Type dropdown
  And the employee sets the Start Date to "2025-08-01"
  And the employee sets the End Date to "2025-08-05"
  And the employee enters a reason with 501 characters in the Reason field
  When the employee clicks the "Submit" button
  Then the form is NOT submitted
  And an inline validation error is shown below Reason: "Reason cannot exceed 500 characters"
```

### TC-NV-07 · Start date in the past

```gherkin
@negative @validation
Scenario: Employee enters a start date in the past
  Given the employee selects "Annual Leave" from the Leave Type dropdown
  And the employee sets the Start Date to "2020-01-01"
  And the employee sets the End Date to "2020-01-05"
  When the employee clicks the "Submit" button
  Then the form is NOT submitted
  And an inline validation error is shown: "Start date cannot be in the past"
```

### TC-NV-08 · Invalid date format in Start Date

```gherkin
@negative @validation
Scenario: Employee enters an invalid date format in Start Date
  Given the employee selects "Annual Leave" from the Leave Type dropdown
  And the employee types "99/99/9999" directly into the Start Date field
  Then the date picker rejects the invalid input
  And the Start Date field reverts to empty or shows a format error
```

---

## Edge Cases

### TC-EC-01 · Leave spanning two calendar months

```gherkin
@edge_case
Scenario: Employee submits a leave request spanning across two calendar months
  Given the employee selects "Annual Leave" from the Leave Type dropdown
  And the employee sets the Start Date to "2025-08-25"
  And the employee sets the End Date to "2025-09-05"
  When the employee clicks the "Submit" button
  Then the leave request is created with status "Pending Approval"
  And the duration is correctly calculated across month boundaries
```

### TC-EC-02 · Leave spanning two calendar years

```gherkin
@edge_case
Scenario: Employee submits a leave request spanning across two calendar years
  Given the employee selects "Annual Leave" from the Leave Type dropdown
  And the employee sets the Start Date to "2025-12-29"
  And the employee sets the End Date to "2026-01-02"
  When the employee clicks the "Submit" button
  Then the leave request is created with status "Pending Approval"
  And the duration is correctly calculated across year boundaries
```

### TC-EC-03 · Leave spanning over a weekend

```gherkin
@edge_case
Scenario: Leave request spanning over a weekend is accepted
  Given the employee selects "Annual Leave" from the Leave Type dropdown
  And the employee sets the Start Date to "2025-08-01" (Friday)
  And the employee sets the End Date to "2025-08-04" (Monday)
  When the employee clicks the "Submit" button
  Then the leave request is created with status "Pending Approval"
  And the system handles weekend days according to business rules
```

### TC-EC-04 · Leave on a public holiday

```gherkin
@edge_case
Scenario: Leave request on a public holiday is accepted or flagged
  Given "2025-08-15" is a configured public holiday
  And the employee selects "Sick Leave" from the Leave Type dropdown
  And the employee sets the Start Date to "2025-08-15"
  And the employee sets the End Date to "2025-08-15"
  When the employee clicks the "Submit" button
  Then the system either accepts with a holiday warning or rejects with an appropriate message
```

### TC-EC-05 · Reason field — exactly 500 characters (upper boundary)

```gherkin
@edge_case
Scenario: Reason field accepts exactly 500 characters (boundary value)
  Given the employee selects "Annual Leave" from the Leave Type dropdown
  And the employee sets the Start Date to "2025-08-01"
  And the employee sets the End Date to "2025-08-05"
  And the employee enters exactly 500 characters in the Reason field
  When the employee clicks the "Submit" button
  Then the leave request is submitted successfully
```

### TC-EC-06 · Reason field — exactly 1 character (lower boundary)

```gherkin
@edge_case
Scenario: Reason field accepts exactly 1 character (minimum boundary)
  Given the employee selects "Annual Leave" from the Leave Type dropdown
  And the employee sets the Start Date to "2025-08-01"
  And the employee sets the End Date to "2025-08-05"
  And the employee enters "A" in the Reason field
  When the employee clicks the "Submit" button
  Then the leave request is submitted successfully
```

### TC-EC-07 · Overlapping date range with existing pending request

```gherkin
@edge_case
Scenario: Employee submits a leave request for an overlapping date range with an existing pending request
  Given the employee already has a pending leave request from "2025-08-01" to "2025-08-05"
  And the employee selects "Annual Leave" from the Leave Type dropdown
  And the employee sets the Start Date to "2025-08-03"
  And the employee sets the End Date to "2025-08-07"
  When the employee clicks the "Submit" button
  Then the system either rejects the request with "You already have a leave request for overlapping dates"
  Or accepts it subject to manager review
```

### TC-EC-08 · Leave request for maximum allowed duration

```gherkin
@edge_case
Scenario: Employee submits leave request for the maximum allowed duration
  Given the employee selects "Annual Leave" from the Leave Type dropdown
  And the employee sets the Start Date to "2025-01-01"
  And the employee sets the End Date to "2025-12-31"
  When the employee clicks the "Submit" button
  Then the system either accepts or rejects based on configured maximum leave duration policy
```

---

## Field-Level Interactions

### Blur events

#### TC-FI-01 · Leave Type shows error on blur when empty

```gherkin
@field_interaction @blur
Scenario: Validation error shown on Leave Type blur when left empty
  Given the employee focuses on the Leave Type dropdown
  And the employee does not make a selection
  When the employee moves focus away from the Leave Type field (blur)
  Then an inline error is displayed: "Leave type is required"
  And the error is visible before the Submit button is clicked
```

#### TC-FI-02 · Start Date shows error on blur when empty

```gherkin
@field_interaction @blur
Scenario: Validation error shown on Start Date blur when left empty
  Given the employee focuses on the Start Date field
  And the employee does not enter a value
  When the employee moves focus away from the Start Date field (blur)
  Then an inline error is displayed: "Start date is required"
```

#### TC-FI-03 · End Date shows error on blur when empty

```gherkin
@field_interaction @blur
Scenario: Validation error shown on End Date blur when left empty
  Given the employee focuses on the End Date field
  And the employee does not enter a value
  When the employee moves focus away from the End Date field (blur)
  Then an inline error is displayed: "End date is required"
```

#### TC-FI-04 · Cross-field date validation triggers on End Date blur

```gherkin
@field_interaction @blur
Scenario: Cross-field date validation triggers on End Date blur
  Given the employee sets the Start Date to "2025-08-10"
  And the employee enters "2025-08-05" in the End Date field
  When the employee moves focus away from the End Date field (blur)
  Then an inline error is displayed: "End date cannot be earlier than start date"
```

### Focus events

#### TC-FI-05 · Error clears when Leave Type is corrected on focus

```gherkin
@field_interaction @focus
Scenario: Validation error clears when employee focuses and corrects Leave Type
  Given the Leave Type validation error is currently displayed
  When the employee focuses on the Leave Type dropdown
  And selects "Annual Leave"
  And moves focus away
  Then the validation error for Leave Type disappears
```

#### TC-FI-06 · End Date picker constrained by Start Date on focus

```gherkin
@field_interaction @focus
Scenario: End Date field is pre-populated or constrained based on Start Date selection
  Given the employee sets the Start Date to "2025-08-01"
  When the employee focuses on the End Date field
  Then the End Date date picker disables all dates before "2025-08-01"
  Or the End Date is auto-populated with "2025-08-01" as default
```

#### TC-FI-07 · Character counter appears in Reason field on focus

```gherkin
@field_interaction @focus
Scenario: Character counter appears in Reason field on focus
  When the employee clicks into the Reason textarea
  Then a character counter is displayed showing "0 / 500"
  And the counter updates in real-time as the employee types
```

### Real-time interactions

#### TC-FI-08 · Character counter updates live as employee types

```gherkin
@field_interaction @realtime
Scenario: Character counter updates live as employee types in Reason field
  Given the employee has clicked into the Reason field
  When the employee types 100 characters
  Then the character counter displays "100 / 500"
  When the employee types an additional 50 characters
  Then the counter displays "150 / 500"
```

#### TC-FI-09 · Character counter warns and blocks at limit

```gherkin
@field_interaction @realtime
Scenario: Character counter turns red when Reason field approaches the limit
  Given the employee has focused the Reason field
  When the employee types 480 characters
  Then the character counter changes to a warning color (e.g., amber)
  When the employee types 500 characters
  Then the counter turns red and further input is blocked or flagged
```

### Save / submit triggers

#### TC-FI-10 · Submit button disabled until all required fields are valid

```gherkin
@field_interaction @save_trigger
Scenario: Submit button is disabled until all required fields are valid
  Given the leave_request_form is freshly loaded
  Then the Submit button is disabled or visually inactive
  When the employee fills in all required fields with valid values
  Then the Submit button becomes enabled and clickable
```

#### TC-FI-11 · Submit button shows loading state to prevent double submission

```gherkin
@field_interaction @save_trigger
Scenario: Submit button triggers loading state on click to prevent duplicate submissions
  Given all required fields are filled with valid data
  When the employee clicks the "Submit" button
  Then the Submit button enters a loading state (spinner or "Submitting..." label)
  And the Submit button is disabled to prevent re-clicking
  And the loading state resolves once the API response is received
```

#### TC-FI-12 · Form submits via keyboard Enter when Submit is focused

```gherkin
@field_interaction @save_trigger
Scenario: Submitting via keyboard Enter key when Submit button is focused
  Given all required fields are filled with valid data
  And the employee has tabbed focus onto the Submit button
  When the employee presses the "Enter" key
  Then the form is submitted
  And the leave request is created with status "Pending Approval"
```

#### TC-FI-13 · Network error shows message and preserves form data

```gherkin
@field_interaction @save_trigger
Scenario: Network error during submission shows an error message without data loss
  Given all required fields are filled with valid data
  And the network is unavailable
  When the employee clicks the "Submit" button
  Then an error message is displayed: "Submission failed. Please try again."
  And the form data is preserved so the employee does not need to re-enter it
  And the Submit button returns to its enabled state
```

---

## Tag Index

| Tag | Description |
|---|---|
| `@smoke` | Minimum viable test set for CI gate |
| `@happy_path` | Successful submission flows |
| `@negative` | Invalid inputs that must be rejected |
| `@validation` | Field-level and form-level validation rules |
| `@edge_case` | Boundary values, date boundaries, overlap scenarios |
| `@field_interaction` | UI behaviour on individual field events |
| `@blur` | Validation triggered when a field loses focus |
| `@focus` | Behaviour when a field gains focus |
| `@realtime` | Live updates while the user types |
| `@save_trigger` | Submit button state and submission behaviour |
