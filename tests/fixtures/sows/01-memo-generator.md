# Statement of Work: Investment Memo Generator

## 1. Background

The client is a mid-sized asset manager. Its research analysts spend most of
a working day turning a listed company's annual report and quarterly results
into a two-page internal memo for the investment committee. Every memo follows
the same house layout: a summary, the business in brief, the latest numbers
against the prior year, the main risks, and open questions for management.
The client wants a tool that drafts this memo so the analyst only reviews and
edits it.

## 2. Scope

In scope:

- Pulling a company's latest public annual report and quarterly results from
  the regulator's public filings website, given a company identifier.
- Extracting the text and the main financial tables from those filings.
- Drafting each memo section with a large language model, using the client's
  house style guide and two example memos as guidance.
- Rendering the draft into the client's fixed HTML memo template, and
  exporting it to PDF for the committee pack.
- A simple web page where an analyst enters a company identifier, waits for
  the draft, edits it in place and downloads the final file.

Out of scope: trading signals, portfolio data, any connection to the order
management system, and private (non-public) company data.

## 3. Requirements

1. R1. Given a company identifier, fetch that company's most recent annual
   report and the last two quarterly filings from the public filings website.
2. R2. Extract the narrative text and the income statement, balance sheet and
   cash flow tables into a structured form the drafting step can use.
3. R3. Draft all five memo sections; every number in the draft must be traced
   to the filing page it came from, shown as a footnote.
4. R4. Render the draft into the fixed HTML template without changing its
   layout, fonts or section order.
5. R5. Export the final memo to PDF with page numbers and the date of the
   filings used.
6. R6. Keep a history of every draft and every analyst edit for one year, so
   compliance can see what the model wrote and what a person changed.
7. R7. A draft for one company must be ready within five minutes of the
   request.
8. R8. The tool is for the client's own analysts only; it is an internal tool
   and will not be resold or given to third parties.

## 4. Technical context

The client's data team writes Python and will maintain the tool after
handover; anything we build should be in Python so they can own it. The
system will be deployed in the client's own AWS account, inside the existing
research VPC, and must use the client's single sign-on for login.

## 5. Gaps and questions for the client

- How many analysts will use the tool, and how many memos a week do they
  expect at peak, for example around results season?
- What is the monthly budget for hosting and for language model usage? Is
  there a hard ceiling the tool must stop at?
- The style guide and the example memos mention portfolio companies by name.
  Are any of those names confidential, and must they be kept out of anything
  sent to outside services?
- Should the model run through a hosted API or inside the AWS account?
- Who signs off on the footnote format before the pilot?

## 6. Deliverables and timeline

A working pilot in eight weeks, a handover session for the data team, and a
short runbook covering deployment, upgrades and rollback.
