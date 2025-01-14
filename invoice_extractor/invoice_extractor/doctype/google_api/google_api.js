// Copyright (c) 2025, Abhijeet Sutar and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Google API", {
// 	refresh(frm) {

// 	},

frappe.ui.form.on('Google API', {
    default: function (frm) {
        if (frm.doc.default) {
            // Confirm before setting as default
            frappe.confirm(
                'Are you sure you want to set this API as default?',
                function () {
                    // Uncheck 'Default' for all other records
                    frappe.call({
                        method: 'frappe.client.get_list',
                        args: {
                            doctype: 'Google API',
                            filters: [['name', '!=', frm.doc.name], ['default', '=', 1]],
                            fields: ['name']
                        },
                        callback: function (r) {
                            if (r.message) {
                                let updates = r.message.map(function (doc) {
                                    return frappe.call({
                                        method: 'frappe.client.set_value',
                                        args: {
                                            doctype: 'Google API',
                                            name: doc.name,
                                            fieldname: 'default',
                                            value: 0
                                        }
                                    });
                                });

                                // Promise.all(updates).then(() => {
                                //     frappe.msgprint({
                                //         title: 'Success',
                                //         message: 'Default has been updated successfully.',
                                //         indicator: 'green'
                                //     });
                                // });
                            }
                        }
                    });
                    frm.save();
                },
                function () {
                    // Reset the checkbox if the user cancels
                    frm.set_value('default', 0);
                }
            );
        } else {
   			 // Confirm before removing default
   			 frappe.confirm(
   			     'This action will set "Gemini 1.5 Flash" as Default API. Are you sure you want Proceed?',
   			     function () {
   			         // Set "Gemini 1.5 Flash" as default
   			         frappe.call({
   			             method: 'frappe.client.set_value',
   			             args: {
   			                 doctype: 'Google API',
   			                 name: 'Gemini 1.5 Flash',
   			                 fieldname: 'default',
   			                 value: 1
   			             },
   			             callback: function (r) {
			
   			                 // Save the form after the message is displayed
   			                 frm.save();
   			                 // frappe.msgprint({
   			                 //         title: 'Notice',
   			                 //         message: 'Default is set to "Gemini 1.5 Flash".',
   			                 //         indicator: 'blue'
   			                 //     });
   			             }
   			         });
   			     },
   			     function () {
   			         // Reset the checkbox back to checked if the user cancels
   			         frm.set_value('default', 1);
   			     }
   			);
   		}
    }
});


// frappe.ui.form.on('Google API', {
//     default: function (frm) {
//         if (frm.doc.default) {
//             // Confirm before saving the form
//             frappe.confirm(
//                 'Are you sure you want to set this record as default?',
//                 function () {
//                     // Uncheck 'Default' for all other records
//                     frappe.call({
//                         method: 'frappe.client.get_list',
//                         args: {
//                             doctype: 'Google API',
//                             filters: [['name', '!=', frm.doc.name], ['default', '=', 1]],
//                             fields: ['name']
//                         },
//                         callback: function (r) {
//                             if (r.message) {
//                                 r.message.forEach(function (doc) {
//                                     frappe.call({
//                                         method: 'frappe.client.set_value',
//                                         args: {
//                                             doctype: 'Google API',
//                                             name: doc.name,
//                                             fieldname: 'default',
//                                             value: 0
//                                         }
//                                     });
//                                 });
//                             }
//                         }
//                     });
//                     frm.save();
//                 },
//                 function () {
//                     // Reset the checkbox if the user cancels
//                     frm.set_value('default', 0);
//                 }
//             );
//         } else {
//             // If 'Default' is unchecked, set "Gemini 1.5 Flash" as default
//             frappe.call({
//                 method: 'frappe.client.set_value',
//                 args: {
//                     doctype: 'Google API',
//                     name: 'Gemini 1.5 Flash',
//                     fieldname: 'default',
//                     value: 1
//                 },
//                 callback: function (r) {
//                     if (r.message) {
//                         frappe.msgprint({
//                             title: 'Notice',
//                             message: 'Default is set to "Gemini 1.5 Flash".',
//                             indicator: 'blue'
//                         });
//                     } else {
//                         frappe.msgprint({
//                             title: 'Error',
//                             message: 'Record "Gemini 1.5 Flash" not found.',
//                             indicator: 'red'
//                         });
//                     }
//                 }
//             });
//         }
//     }
// });
