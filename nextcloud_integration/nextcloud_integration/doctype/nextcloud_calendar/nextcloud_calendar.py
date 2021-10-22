# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies and contributors
# License: MIT. See LICENSE
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    add_days,
    add_to_date,
    get_datetime,
    get_request_site_address,
    get_time_zone,
    get_weekdays,
    now_datetime,
)
from dateutil import parser

import caldav

nextcloud_calendar_frequencies = {
    "RRULE:FREQ=DAILY": "Daily",
    "RRULE:FREQ=WEEKLY": "Weekly",
    "RRULE:FREQ=MONTHLY": "Monthly",
    "RRULE:FREQ=YEARLY": "Yearly",
}

nextcloud_calendar_days = {
    "MO": "monday",
    "TU": "tuesday",
    "WE": "wednesday",
    "TH": "thursday",
    "FR": "friday",
    "SA": "saturday",
    "SU": "sunday",
}


class NextcloudCalendar(Document):
    def validate(self):
        nextcloud_settings = frappe.get_single("Nextcloud Setting")

        if not nextcloud_settings.calendar_enable:
            frappe.throw(_("Enable Nextcloud Calendar in Nextcloud Settings"))

        if (
            not nextcloud_settings.calendar_user
            or not nextcloud_settings.calendar_password
        ):
            frappe.throw(
                _("Enter Dedicated Calendar User and Password in Nextcloud Settings")
            )

        return nextcloud_settings


def get_nextcloud_calendar_object_if_exists(account, cal_principal):
    """
    Checks if Nextcloud Calendar is present and valid for the user.
    Example URL: https://cloud.nextcloud.../remote.php/dav/calendars/username/calendar_name/
    """
    selected_calendar = None

    account.load_from_db()
    if account.calendar_name:
        all_calendars = cal_principal.calendars()
        if all_calendars:
            for c in all_calendars:
                if c.name == account.calendar_name:
                    selected_calendar = c
                    break

            frappe.msgprint(_("Given user has not given calendar"))
        else:
            frappe.msgprint(_("Server has no calendars for given user"))

    return selected_calendar


def get_nextcloud_calendar_url(n_calendar):
    nextcloud_settings = frappe.get_doc("Nextcloud Settings")
    account = frappe.get_doc("Nextcloud Calendar", n_calendar)

    caldav_url = account.calendar_url[-1]
    if caldav_url[-1] != "/":
        caldav_url += "/"

    caldav_user = nextcloud_settings.calendar_user
    caldav_url = caldav_url + "users/" + caldav_user

    return caldav_url


def get_nextcloud_calendar_object(n_calendar):
    """
    Returns an object of Nextcloud Calendar along with Nextcloud Calendar doc.
    """
    nextcloud_settings = frappe.get_doc("Nextcloud Settings")
    account = frappe.get_doc("Nextcloud Calendar", n_calendar)

    # set connection to caldav calendar with user credentials
    caldav_client = caldav.DAVClient(
        url=get_nextcloud_calendar_url(n_calendar),
        username=nextcloud_settings.calendar_user,
        password=nextcloud_settings.calendar_password,
    )
    cal_principal = caldav_client.principal()

    nextcloud_calendar = get_nextcloud_calendar_object_if_exists(account, cal_principal)

    return nextcloud_calendar, account


@frappe.whitelist()
def sync(n_calendar=None):
    filters = {"enable": 1}

    if n_calendar:
        filters.update({"name": n_calendar})

    nextcloud_calendars = frappe.get_list("Nextcloud Calendar", filters=filters)

    for n in nextcloud_calendars:
        return sync_events_from_nextcloud_calendar(n.name)


def insert_nextcloud_event_to_calendar(account, event, recurrence=None):
    """
    Inserts event in Frappe Calendar during Sync
    """
    calendar_event = {
        "doctype": "Event",
        "subject": event.get("summary"),
        "description": event.get("description"),
        "nextcloud_calendar_event": 1,
        "nextcloud_calendar": account.name,
        "nextcloud_calendar_id": account.nextcloud_calendar_id,
        "nextcloud_calendar_event_id": event.get("id"),
        "pulled_from_nextcloud_calendar": 1,
    }
    calendar_event.update(
        nextcloud_calendar_to_repeat_on(
            recurrence=recurrence, start=event.get("start"), end=event.get("end")
        )
    )
    frappe.get_doc(calendar_event).insert(ignore_permissions=True)


def nextcloud_calendar_to_repeat_on(start, end, recurrence=None):
    """
    recurrence is in the form ['RRULE:FREQ=WEEKLY;BYDAY=MO,TU,TH']
    has the frequency and then the days on which the event recurs

    Both have been mapped in a dict for easier mapping.
    """
    repeat_on = {
        "starts_on": get_datetime(start.get("date"))
        if start.get("date")
        else parser.parse(start.get("dateTime")).utcnow(),
        "ends_on": get_datetime(end.get("date"))
        if end.get("date")
        else parser.parse(end.get("dateTime")).utcnow(),
        "all_day": 1 if start.get("date") else 0,
        "repeat_this_event": 1 if recurrence else 0,
        "repeat_on": None,
        "repeat_till": None,
        "sunday": 0,
        "monday": 0,
        "tuesday": 0,
        "wednesday": 0,
        "thursday": 0,
        "friday": 0,
        "saturday": 0,
    }

    # recurrence rule "RRULE:FREQ=WEEKLY;BYDAY=MO,TU,TH"
    if recurrence:
        # nextcloud_calendar_frequency = RRULE:FREQ=WEEKLY, byday = BYDAY=MO,TU,TH, until = 20191028
        nextcloud_calendar_frequency, until, byday = get_recurrence_parameters(
            recurrence
        )
        repeat_on["repeat_on"] = nextcloud_calendar_frequencies.get(
            nextcloud_calendar_frequency
        )

        if repeat_on["repeat_on"] == "Daily":
            repeat_on["ends_on"] = None
            repeat_on["repeat_till"] = (
                datetime.strptime(until, "%Y%m%d") if until else None
            )

        if byday and repeat_on["repeat_on"] == "Weekly":
            repeat_on["repeat_till"] = (
                datetime.strptime(until, "%Y%m%d") if until else None
            )
            byday = byday.split("=")[1].split(",")
            for repeat_day in byday:
                repeat_on[nextcloud_calendar_days[repeat_day]] = 1

        if byday and repeat_on["repeat_on"] == "Monthly":
            byday = byday.split("=")[1]
            repeat_day_week_number, repeat_day_name = None, None

            for num in ["-2", "-1", "1", "2", "3", "4", "5"]:
                if num in byday:
                    repeat_day_week_number = num
                    break

            for day in ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]:
                if day in byday:
                    repeat_day_name = nextcloud_calendar_days.get(day)
                    break

            # Only Set starts_on for the event to repeat monthly
            start_date = parse_nextcloud_calendar_recurrence_rule(
                int(repeat_day_week_number), repeat_day_name
            )
            repeat_on["starts_on"] = start_date
            repeat_on["ends_on"] = add_to_date(start_date, minutes=5)
            repeat_on["repeat_till"] = (
                datetime.strptime(until, "%Y%m%d") if until else None
            )

        if repeat_on["repeat_till"] == "Yearly":
            repeat_on["ends_on"] = None
            repeat_on["repeat_till"] = (
                datetime.strptime(until, "%Y%m%d") if until else None
            )

    return repeat_on


def update_event_in_calendar(account, event, recurrence=None):
    """
    Updates Event in Frappe Calendar if any existing Nextcloud Calendar Event is updated
    """
    calendar_event = frappe.get_doc(
        "Event", {"nextcloud_calendar_event_id": event.get("id")}
    )
    calendar_event.subject = event.get("summary")
    calendar_event.description = event.get("description")
    calendar_event.update(
        nextcloud_calendar_to_repeat_on(
            recurrence=recurrence, start=event.get("start"), end=event.get("end")
        )
    )
    calendar_event.save(ignore_permissions=True)


def sync_events_from_nextcloud_calendar(n_calendar, method=None):
    """
    Syncs Events from Nextcloud Calendar in Framework Calendar.
    """
    nextcloud_calendar, account = get_nextcloud_calendar_object(n_calendar)

    if not nextcloud_calendar or not account.pull_from_nextcloud_calendar:
        return

    events = frappe._dict()
    results = []
    while True:
        events = nextcloud_calendar.events()

        for event in events.get("items", []):
            results.append(event)

        # if not events.get("nextPageToken"):
        #     if events.get("nextSyncToken"):
        #         account.next_sync_token = events.get("nextSyncToken")
        #         account.save()
        #     break

    for idx, event in enumerate(results):
        frappe.publish_realtime(
            "import_nextcloud_calendar",
            dict(progress=idx + 1, total=len(results)),
            user=frappe.session.user,
        )

        # If Nextcloud Calendar Event if confirmed, then create an Event
        if event.get("status") == "confirmed":
            recurrence = None
            if event.get("recurrence"):
                try:
                    recurrence = event.get("recurrence")[0]
                except IndexError:
                    pass

            if not frappe.db.exists(
                "Event", {"nextcloud_calendar_event_id": event.get("id")}
            ):
                insert_nextcloud_event_to_calendar(account, event, recurrence)
            else:
                update_event_in_calendar(account, event, recurrence)
        elif event.get("status") == "cancelled":
            # If any synced Nextcloud Calendar Event is cancelled, then close the Event
            frappe.db.set_value(
                "Event",
                {
                    "nextcloud_calendar_id": account.nextcloud_calendar_id,
                    "nextcloud_calendar_event_id": event.get("id"),
                },
                "status",
                "Closed",
            )
            frappe.get_doc(
                {
                    "doctype": "Comment",
                    "comment_type": "Info",
                    "reference_doctype": "Event",
                    "reference_name": frappe.db.get_value(
                        "Event",
                        {
                            "nextcloud_calendar_id": account.nextcloud_calendar_id,
                            "nextcloud_calendar_event_id": event.get("id"),
                        },
                        "name",
                    ),
                    "content": " - Event deleted from Nextcloud Calendar.",
                }
            ).insert(ignore_permissions=True)
        else:
            pass

    if not results:
        return _("No Nextcloud Calendar Event to sync.")
    elif len(results) == 1:
        return _("1 Nextcloud Calendar Event synced.")
    else:
        return _("{0} Nextcloud Calendar Events synced.").format(len(results))


def parse_nextcloud_calendar_recurrence_rule(repeat_day_week_number, repeat_day_name):
    """
    Returns (repeat_on) exact date for combination eg 4TH viz. 4th thursday of a month
    """
    if repeat_day_week_number < 0:
        # Consider a month with 5 weeks and event is to be repeated in last week of every month, nextcloud caledar considers
        # a month has 4 weeks and hence itll return -1 for a month with 5 weeks.
        repeat_day_week_number = 4

    weekdays = get_weekdays()
    current_date = now_datetime()
    isset_day_name, isset_day_number = False, False

    # Set the proper day ie if recurrence is 4TH, then align the day to Thursday
    while not isset_day_name:
        isset_day_name = (
            True
            if weekdays[current_date.weekday()].lower() == repeat_day_name
            else False
        )
        current_date = add_days(current_date, 1) if not isset_day_name else current_date

    # One the day is set to Thursday, now set the week number ie 4
    while not isset_day_number:
        week_number = get_week_number(current_date)
        isset_day_number = True if week_number == repeat_day_week_number else False
        # check if  current_date week number is greater or smaller than repeat_day week number
        weeks = 1 if week_number < repeat_day_week_number else -1
        current_date = (
            add_to_date(current_date, weeks=weeks)
            if not isset_day_number
            else current_date
        )

    return current_date


def get_week_number(dt):
    """
    Returns the week number of the month for the specified date.
    https://stackoverflow.com/questions/3806473/python-week-number-of-the-month/16804556
    """
    from math import ceil

    first_day = dt.replace(day=1)

    dom = dt.day
    adjusted_dom = dom + first_day.weekday()

    return int(ceil(adjusted_dom / 7.0))


def get_recurrence_parameters(recurrence):
    recurrence = recurrence.split(";")
    frequency, until, byday = None, None, None

    for r in recurrence:
        if "RRULE:FREQ" in r:
            frequency = r
        elif "UNTIL" in r:
            until = r
        elif "BYDAY" in r:
            byday = r
        else:
            pass

    return frequency, until, byday
