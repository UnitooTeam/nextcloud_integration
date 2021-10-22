// Copyright (c) 2021, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Nextcloud Calendar", {
  refresh: function (frm) {
    if (frm.is_new()) {
      frm.dashboard.set_headline(
        __("To use Nextcloud Calendar, enable {0}.", [
          `<a href='/app/nextcloud-settings'>${__("Nextcloud Settings")}</a>`,
        ])
      );
    }

    frappe.realtime.on("import_nextcloud_calendar", (data) => {
      if (data.progress) {
        frm.dashboard.show_progress(
          "Syncing Nextcloud Calendar",
          (data.progress / data.total) * 100,
          __("Syncing {0} of {1}", [data.progress, data.total])
        );
        if (data.progress === data.total) {
          frm.dashboard.hide_progress("Syncing Nextcloud Calendar");
        }
      }
    });

    if (frm.doc.refresh_token) {
      frm.add_custom_button(__("Sync Calendar"), function () {
        frappe.show_alert({
          indicator: "green",
          message: __("Syncing"),
        });
        frappe
          .call({
            method:
              "frappe.integrations.doctype.nextcloud_calendar.nextcloud_calendar.sync",
            args: {
              n_calendar: frm.doc.name,
            },
          })
          .then((r) => {
            frappe.hide_progress();
            frappe.msgprint(r.message);
          });
      });
    }
  },
});
