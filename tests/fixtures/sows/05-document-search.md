# Statement of Work: Internal Document Search

## 1. Background

The client is an engineering consultancy with offices in several cities.
Twenty years of project reports, design calculations, drawings registers and
meeting minutes sit across network drives and an old document management
system. Engineers cannot find earlier work that would save them days, so the
same studies are redone. The client wants one search box over all of these
documents that understands what an engineer is asking, not only the exact
words.

The documents name the client's own customers and past projects. Keep these
names private: the names to keep private are every customer name and project
name found in the documents, and no search query sent outside the client's
systems may contain them.

## 2. Scope

In scope:

- Indexing documents from the network drives and the document management
  system: PDF, Word, Excel and plain text, including scanned PDFs.
- Keyword search and meaning-based (semantic) search over the same index,
  with results ranked together.
- Filters by office, year, document type and discipline.
- Respecting the existing folder permissions, so nobody sees a result they
  could not open today.
- A web search page with result previews and a link to the source file.

Out of scope: editing documents, moving them out of their current stores,
and a chat assistant that writes answers (a possible later phase).

## 3. Requirements

1. R1. Index all supported file types, including text from scanned PDFs.
2. R2. Pick up new and changed documents within one hour.
3. R3. Combine keyword and semantic search results into one ranked list.
4. R4. Apply the existing folder permissions to every result, using the
   client's directory groups.
5. R5. Show a preview with the matching passage highlighted.
6. R6. Return results within two seconds for a typical query.
7. R7. The system must run on Azure, in the client's existing subscription,
   and use the client's Entra ID sign-in.
8. R8. It is an internal tool for the client's own staff only and will not be
   distributed outside the company.
9. R9. The client's IT team writes Python, so services we build must be in
   Python.

## 4. Gaps and questions for the client

- How many documents and how many gigabytes are there in total, and how fast
  is the collection growing?
- How many engineers will search at the same time at peak?
- What is the monthly budget for hosting, indexing and any embedding model
  usage, and is there a hard ceiling?
- Can the old document management system export its files and permissions,
  or must we read them through its API?
- Which offices go first in the pilot?

## 5. Deliverables and timeline

A pilot over two offices' documents in eight weeks, then the rest of the
collection. Deliverables are the indexing service, the search page, a
relevance test on 100 real queries collected from engineers, and an
operations guide covering re-indexing and permission checks.
