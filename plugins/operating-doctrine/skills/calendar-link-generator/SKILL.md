---
name: calendar-link-generator
description: Builds add-to-calendar links (Google Calendar, Outlook.com, Outlook for Microsoft 365) for an event Allison describes, following her nine standing rules for titles, timing, location, description, guests and link display. Use this whenever she asks for a calendar link, an add-to-calendar link, a calendar invite link, "put this on a calendar," or describes a meeting, lunch, call or appointment and wants it on Google or Outlook, even if she doesn't say the word "link."
---

# Calendar Link Generator

Turn an event description into ready-to-click add-to-calendar links. The goal is that Allison can describe an event in one breath and get back links she can click immediately, with nothing missing and nothing asked twice.

## The nine rules

1. Title format is "Purpose - Name & Name." Use full names whenever she gives them (for example "Lunch - Don Hobbs & Allison Gaddy"). The purpose is a short word or phrase (Lunch, Coffee, Listing Appointment, Strategy Call). Allison Gaddy is the organizer, so include her name as one of the names unless the event clearly isn't hers.
2. Default length is 1 hour. Use her end time or duration when she gives one.
3. Use Central time (America/Chicago) unless she says otherwise or the location is clearly in another time zone, in which case use that zone.
4. Resolve relative dates (tomorrow, Friday, next Thursday) from today's actual date in her time zone. Check the current date rather than assuming it. If "next Thursday" is genuinely ambiguous, use the Thursday of next week and state the date in the reply so she can catch it.
5. Always include a location. Use the venue and area she gives (for example "North Italia, Legacy West, Plano, TX"). For a call or video meeting, use the platform (Zoom, Phone) or the meeting link she provides.
6. Write a short, useful description, one or two sentences on who and why. For a client event, if the description would be thin without context, ask her exactly one question (who it's with and what they should know), then write the notes from her answer. Don't ask for anything she already gave.
7. When she names guests and gives their email addresses, add them as guests on every link. Never invent an email address.
8. Never show raw URLs. Present each link as a labeled markdown hyperlink, like [Add to Google Calendar](url).
9. Never ask for anything she already told you in this conversation, in this message or earlier.

## Building the links

Convert start and end times to UTC and write them in UTC on every link, so the event lands at the correct local time whatever zone the recipient's calendar uses. Mind daylight saving time. Central is UTC-6 in standard time (early November to mid-March) and UTC-5 in daylight time. When unsure of the offset for the date, compute it (for example with Python's zoneinfo) rather than guessing.

URL-encode every parameter value. Spaces become %20, "&" in a title becomes %26, "," becomes %2C, "@" in an email becomes %40, newlines in a description become %0A.

Google Calendar
```
https://calendar.google.com/calendar/render?action=TEMPLATE
  &text={title}
  &dates={startUTC}/{endUTC}          format YYYYMMDDTHHMMSSZ, e.g. 20261110T183000Z
  &details={description}
  &location={location}
  &add={guest1},{guest2}             only when guest emails were given
```

Outlook.com (personal accounts)
```
https://outlook.live.com/calendar/0/action/compose?subject={title}
  &startdt={startUTC}&enddt={endUTC}  format YYYY-MM-DDTHH:MM:SSZ, e.g. 2026-11-10T18:30:00Z
  &body={description}
  &location={location}
  &to={guest1},{guest2}              only when guest emails were given
  &path=%2Fcalendar%2Faction%2Fcompose&rru=addevent
```

Outlook for Microsoft 365 (work accounts)
Same as Outlook.com with the host changed to `https://outlook.office.com`.

Join each URL into a single line with no spaces before presenting it.

For an all-day event, Google uses `dates=YYYYMMDD/YYYYMMDD` (end date is the day after), and Outlook uses `startdt=YYYY-MM-DD&enddt=YYYY-MM-DD&allday=true`.

## Reply format

Keep the reply short. One line confirming the title, day, date, time range with zone, and location, plus a note that guests were added if any were. Then the three labeled links, each on its own line.

[Add to Google Calendar](...)
[Add to Outlook.com](...)
[Add to Outlook (Microsoft 365)](...)

Follow Allison's standing formatting preferences in the reply. No bold, italics, em dashes or en dashes, and no colons or semicolons in prose.

## Example

Request. "Calendar link for tomorrow's lunch with Don Hobbs (don@expertpartners.com) at North Italia in Legacy West at 12:30." Today is Monday, November 9, 2026.

Result. Title "Lunch - Don Hobbs & Allison Gaddy," Tuesday, November 10, 12:30 to 1:30 PM Central (18:30 to 19:30 UTC), location "North Italia, Legacy West, Plano, TX," description "Lunch with Don Hobbs at North Italia in Legacy West," guest don@expertpartners.com.

[Add to Google Calendar](https://calendar.google.com/calendar/render?action=TEMPLATE&text=Lunch%20-%20Don%20Hobbs%20%26%20Allison%20Gaddy&dates=20261110T183000Z/20261110T193000Z&details=Lunch%20with%20Don%20Hobbs%20at%20North%20Italia%20in%20Legacy%20West.&location=North%20Italia%2C%20Legacy%20West%2C%20Plano%2C%20TX&add=don%40expertpartners.com)
