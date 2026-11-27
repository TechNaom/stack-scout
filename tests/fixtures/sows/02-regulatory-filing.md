# Statement of Work: Customs and Safety Filing Assistant

Client: Halvorsen Freight

## 1. Background

Halvorsen Freight runs road and rail freight across several countries. Each
shipment of regulated goods needs a set of customs declarations and safety
filings, and each country has its own forms, deadlines and rules. Today a
compliance team of about 60 people fills these forms by hand from shipping
documents, chases missing data by email, and keeps deadlines in shared
spreadsheets. Late or wrong filings lead to fines and held cargo.

The client's name and its customers' names are commercially sensitive. Keep
the client's name confidential: it must not appear in any search, any outside
service request or any public issue tracker. The names to keep private are
the client's name and the names in the shipping documents.

## 2. Scope

In scope:

- Reading incoming shipping documents (PDF and scanned images) and pulling
  out the fields each filing needs.
- Filling the right filing forms for each country from those fields.
- A review and approval step before anything is submitted.
- Deadline tracking with reminders for every open filing.
- A full audit trail of who changed, approved and submitted each filing.

Out of scope: direct electronic submission to customs systems in this phase
(the team will still upload the approved forms by hand), invoicing and route
planning.

## 3. Requirements

1. R1. Extract shipper, consignee, goods description, hazard class, weights
   and dates from shipping documents, including scanned pages.
2. R2. Flag any field that could not be read with confidence, and never guess
   a value for it.
3. R3. Fill the filing forms for the first three countries from the extracted
   fields; form layouts are supplied by the client.
4. R4. Route every completed filing to a reviewer; only an approved filing
   can be exported.
5. R5. Track each filing's deadline and send reminders at seven days, two
   days and on the day.
6. R6. Record every change, approval and export in an audit log that cannot
   be edited, kept for seven years.
7. R7. Support about 60 internal users and around 3,000 filings a month,
   rising to about 5,000 at peak season.
8. R8. The budget for hosting and running the system is $400 a month,
   including any document reading service.
9. R9. Role-based access: preparers, reviewers and administrators.

## 4. Gaps and questions for the client

- Which programming languages does the client's IT team know, and who will
  maintain the system after handover?
- Where should the system run: on premises, or with a cloud provider, and if
  so which one? Are there data residency rules for shipment data?
- Is this only for the client's own compliance team, or does the client plan
  to offer it to its freight customers or partners later?
- Which form versions are current for each country, and who keeps them up to
  date when the rules change?
- What accuracy do reviewers need before they trust the extracted fields?

## 5. Deliverables and timeline

A pilot covering one country in ten weeks, then the other two countries in a
second phase. Deliverables are the working system, an administrator guide and
a test report showing extraction accuracy on a sample of 200 real documents
supplied by the client.
