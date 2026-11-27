# Statement of Work: Support Ticket Triage

## 1. Background

The client runs customer support for a consumer electronics brand. Tickets
arrive by email, through a web contact form and from a chat widget, and all
land in one shared queue. Support agents read each ticket, decide what it is
about and how urgent it is, and pass it to the right group: billing,
returns, technical help or complaints. Sorting the queue takes a large part
of every shift, urgent tickets wait behind routine ones, and the same
question is often answered in different ways.

The client wants an assistant that reads each new ticket, labels its topic
and urgency, routes it to the right group, and suggests a first reply from
the existing help articles for the agent to check and send.

## 2. Scope

In scope:

- Collecting new tickets from the email inbox, the contact form and the chat
  widget into one place.
- Classifying each ticket by topic and urgency.
- Routing each ticket to the right group queue.
- Suggesting a draft reply based on the client's help articles.
- A dashboard of ticket volume, topic mix, waiting time and how often agents
  accept the suggested reply.

Out of scope: replacing the agents, sending any reply without an agent's
approval, and voice calls.

## 3. Requirements

1. R1. Collect tickets from all three channels within one minute of arrival.
2. R2. Label each ticket with one of the client's 12 topics and one of three
   urgency levels.
3. R3. Route each ticket to its group queue; tickets the classifier is unsure
   about go to a human sorting queue.
4. R4. Suggest a draft reply for the five most common topics, citing the help
   articles it used.
5. R5. Never send a reply without an agent's explicit approval.
6. R6. Detect a customer's language and route non-English tickets to the
   agents who speak that language.
7. R7. Handle about 2,000 tickets a day across about 35 agents, with peaks of
   three times that after a product launch.
8. R8. Show a daily dashboard of volume, topic mix, waiting time and
   suggestion acceptance rate.
9. R9. Mask card numbers and phone numbers in tickets before any text leaves
   the support system.

## 4. Gaps and questions for the client

- Which helpdesk product does the client use today, and does it have an API
  we can read from and write to?
- Which programming languages does the client's team work in, and who will
  maintain the triage service?
- Where must the service be hosted, and are there rules on where customer
  data may be stored?
- What is the monthly budget for hosting and for any language model usage?
- Is this only for the client's own support team, or will it be offered to
  other brands the client supports?
- Customer names and the brand's name appear in every ticket. Which names, if
  any, must be kept out of outside services and searches?
- How are the 12 topics defined today, and is there a labelled history of
  past tickets we can learn from?

## 5. Deliverables and timeline

A pilot on the email channel in six weeks, then the contact form and chat
widget. Deliverables are the triage service, the dashboard, a measured
accuracy report on 500 past tickets, and an operations guide.
