// Copyright (c) 2024, Abhijeet Sutar and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Upload Customer PO", {
// 	refresh(frm) {
// 		if (frm.doc.docstatus == 0 && frm.doc.attach_copy) {
//             frm.add_custom_button(__("Create SO"), function () {
//                 frappe.call({
//                     method: 'invoice_extractor.invoice_extractor.doctype.upload_customer_po.upload_customer_po.create_sales_order_from_po',
//                     args: { doc: frm.doc },
//                     callback: function (r) {
//                         if (r.message) {
//                             frappe.msgprint({
//                                 title: __("Success"),
//                                 message: r.message,
//                                 indicator: "green"
//                             });
//                             frm.refresh();
//                         }
//                     },
//                 });
//             }).css({ 'background-color': '#0F7BFE', 'color': 'white' });
//         }
// 	},
// });

frappe.ui.form.on("Upload Customer PO", {
    refresh(frm) {
        if (frm.doc.docstatus == 0 && frm.doc.attach_copy) {
            frm.add_custom_button(__("Create SO"), function () {
                // Create loading box with a rotating circle
                var $loadingBox = $('<div class="loading-overlay"><span class="processing-text">Processing...</span><div class="loading-circle"></div></div>')
                    .css({ 
                        'position': 'fixed',
                        'top': '50%',
                        'left': '50%',
                        'transform': 'translate(-50%, -50%)',
                        'background-color': '#f0f0f0', 
                        'padding': '30px', 
                        'border-radius': '10px',
                        'text-align': 'center',
                        'z-index': '9999', // Ensure it appears on top of everything
                        'box-shadow': '0 4px 10px rgba(0, 0, 0, 0.3)', // Dark grey shadow around the box
                        'width': '300px',  // Adjust the width as needed
                        'height': '150px', // Adjust the height as needed
                    });
                
                $('body').append($loadingBox);

                // CSS for rotating circle and its center alignment
                var style = `
                    .loading-circle {
                        border: 4px solid #f3f3f3;
                        border-top: 4px solid #0F7BFE;
                        border-radius: 50%;
                        width: 30px;
                        height: 30px;
                        animation: spin 1s linear infinite;
                        margin-top: 15px; /* Adjusted margin */
                        margin-left: auto;
                        margin-right: auto;
                    }
                    .loading-overlay {
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                    }
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                `;
                $('head').append('<style>' + style + '</style>');

                frappe.call({
                    method: 'invoice_extractor.invoice_extractor.doctype.upload_customer_po.upload_customer_po.create_sales_order_from_po',
                    args: { doc: frm.doc },
                    callback: function (r) {
                        // Hide loading box and show success message with green tickmark
                        $loadingBox.remove();
                        
                        if (r.message) {
                            var $successBox = $('<div class="success-overlay"><span class="green-tick">&#10004;</span> ' + __("Success") + '</div>')
                                .css({ 
                                    'position': 'fixed',
                                    'top': '50%',
                                    'left': '50%',
                                    'transform': 'translate(-50%, -50%)',
                                    'background-color': '#D4EDDA',
                                    'padding': '20px',
                                    'border-radius': '10px',
                                    'color': '#155724',
                                    'text-align': 'center',
                                    'z-index': '9999',
                                    'display': 'inline-block',
                                    'box-shadow': '0 4px 10px rgba(0, 0, 0, 0.3)', // Dark grey shadow for success box
                                });
                            $('body').append($successBox);
                            frm.refresh();
                        }
                    },
                    error: function (r) {
                        // Hide loading box and show error message
                        $loadingBox.remove();
                        
                        var $errorBox = $('<div class="error-overlay"><span class="red-tick">&#10060;</span> ' + __("Error occurred while creating Sales Order.") + '</div>')
                            .css({ 
                                'position': 'fixed',
                                'top': '50%',
                                'left': '50%',
                                'transform': 'translate(-50%, -50%)',
                                'background-color': '#f8d7da',
                                'padding': '20px',
                                'border-radius': '10px',
                                'color': '#721c24',
                                'text-align': 'center',
                                'z-index': '9999',
                                'display': 'inline-block',
                                'box-shadow': '0 4px 10px rgba(0, 0, 0, 0.3)', // Dark grey shadow for error box
                            });
                        $('body').append($errorBox);

                        // Close the error box if clicked outside
                        $(document).on('click', function (event) {
                            if (!$(event.target).closest($errorBox).length) {
                                $errorBox.remove();
                            }
                        });
                    }
                });
            }).css({ 'background-color': '#0F7BFE', 'color': 'white' });
        }
    },
});



// frappe.ui.form.on("Upload Customer PO", {
//     refresh(frm) {
//         if (frm.doc.docstatus == 0 && frm.doc.attach_copy) {
//             frm.add_custom_button(__("Create SO"), function () {
//                 // Create loading box with a rotating circle
//                 var $loadingBox = $('<div class="loading-overlay"><span class="processing-text">Processing...</span><div class="loading-circle"></div></div>')
//                     .css({ 
//                         'position': 'fixed',
//                         'top': '50%',
//                         'left': '50%',
//                         'transform': 'translate(-50%, -50%)',
//                         'background-color': '#f0f0f0', 
//                         'padding': '30px', 
//                         'border-radius': '10px',
//                         'text-align': 'center',
//                         'z-index': '9999', // Ensure it appears on top of everything
//                         'box-shadow': '0 4px 10px rgba(0, 0, 0, 0.3)', // Dark grey shadow around the box
//                         'width': '400px',  // Adjust the width as needed
//                         'height': '180px', // Adjust the height as needed
//                     });
                
//                 $('body').append($loadingBox);

//                 // CSS for rotating circle and its center alignment
//                 var style = `
//                     .loading-circle {
//                         border: 4px solid #f3f3f3;
//                         border-top: 4px solid #0F7BFE;
//                         border-radius: 50%;
//                         width: 30px;
//                         height: 30px;
//                         animation: spin 1s linear infinite;
//                         margin-top: 15px; /* Adjusted margin */
//                         margin-left: auto;
//                         margin-right: auto;
//                     }
//                     .loading-overlay {
//                         display: flex;
//                         flex-direction: column;
//                         align-items: center;
//                         justify-content: center;
//                     }
//                     @keyframes spin {
//                         0% { transform: rotate(0deg); }
//                         100% { transform: rotate(360deg); }
//                     }
//                 `;
//                 $('head').append('<style>' + style + '</style>');

//                 frappe.call({
//                     method: 'invoice_extractor.invoice_extractor.doctype.upload_customer_po.upload_customer_po.create_sales_order_from_po',
//                     args: { doc: frm.doc },
//                     callback: function (r) {
//                         // Hide loading box and show success message with green tickmark
//                         $loadingBox.remove();
                        
//                         if (r.message) {
//                             var $successBox = $('<div class="success-overlay"><span class="green-tick">&#10004;</span> ' + __("Success") + '</div>')
//                                 .css({ 
//                                     'position': 'fixed',
//                                     'top': '50%',
//                                     'left': '50%',
//                                     'transform': 'translate(-50%, -50%)',
//                                     'background-color': '#D4EDDA',
//                                     'padding': '20px',
//                                     'border-radius': '10px',
//                                     'color': '#155724',
//                                     'text-align': 'center',
//                                     'z-index': '9999',
//                                     'display': 'inline-block',
//                                     'box-shadow': '0 4px 10px rgba(0, 0, 0, 0.3)', // Dark grey shadow for success box
//                                 });
//                             $('body').append($successBox);
//                             frm.refresh();
//                         }
//                     },
//                     error: function (r) {
//                         // Hide loading box and show error message
//                         $loadingBox.remove();
                        
//                         var $errorBox = $('<div class="error-overlay"><span class="red-tick">&#10060;</span> ' + __("Error occurred while creating Sales Order.") + '</div>')
//                             .css({ 
//                                 'position': 'fixed',
//                                 'top': '50%',
//                                 'left': '50%',
//                                 'transform': 'translate(-50%, -50%)',
//                                 'background-color': '#f8d7da',
//                                 'padding': '20px',
//                                 'border-radius': '10px',
//                                 'color': '#721c24',
//                                 'text-align': 'center',
//                                 'z-index': '9999',
//                                 'display': 'inline-block',
//                                 'box-shadow': '0 4px 10px rgba(0, 0, 0, 0.3)', // Dark grey shadow for error box
//                             });
//                         $('body').append($errorBox);
//                     }
//                 });
//             }).css({ 'background-color': '#0F7BFE', 'color': 'white' });
//         }
//     },
// });




// frappe.ui.form.on("Upload Customer PO", {
//     refresh(frm) {
//         if (frm.doc.docstatus == 0 && frm.doc.attach_copy) {
//             frm.add_custom_button(__("Create SO"), function () {
//                 // Create loading box with a rotating circle
//                 var $loadingBox = $('<div class="loading-overlay"><span class="processing-text">Processing...</span><div class="loading-circle"></div></div>')
//                     .css({ 
//                         'position': 'fixed',
//                         'top': '50%',
//                         'left': '50%',
//                         'transform': 'translate(-50%, -50%)',
//                         'background-color': '#f0f0f0', 
//                         'padding': '30px', 
//                         'border-radius': '10px',
//                         'text-align': 'center',
//                         'z-index': '9999', // Ensure it appears on top of everything
//                         'box-shadow': '0 4px 10px rgba(0, 0, 0, 0.3)', // Dark grey shadow around the box
//                         'width': '400px',  // Adjust the width as needed
//                         'height': '200px', // Adjust the height as needed
//                     });
                
//                 $('body').append($loadingBox);

//                 // CSS for rotating circle and its center alignment
//                 var style = `
//                     .loading-circle {
//                         border: 4px solid #f3f3f3;
//                         border-top: 4px solid #0F7BFE;
//                         border-radius: 50%;
//                         width: 30px;
//                         height: 30px;
//                         animation: spin 1s linear infinite;
//                         margin-top: 15px; /* Adjusted margin */
//                         margin-left: auto;
//                         margin-right: auto;
//                     }
//                     .loading-overlay {
//                         display: flex;
//                         flex-direction: column;
//                         align-items: center;
//                         justify-content: center;
//                     }
//                     @keyframes spin {
//                         0% { transform: rotate(0deg); }
//                         100% { transform: rotate(360deg); }
//                     }
//                 `;
//                 $('head').append('<style>' + style + '</style>');

//                 frappe.call({
//                     method: 'invoice_extractor.invoice_extractor.doctype.upload_customer_po.upload_customer_po.create_sales_order_from_po',
//                     args: { doc: frm.doc },
//                     callback: function (r) {
//                         // Hide loading box and show success message with green tickmark
//                         $loadingBox.remove();
                        
//                         if (r.message) {
//                             var $successBox = $('<div class="success-overlay"><span class="green-tick">&#10004;</span> ' + __("Success") + '</div>')
//                                 .css({ 
//                                     'position': 'fixed',
//                                     'top': '50%',
//                                     'left': '50%',
//                                     'transform': 'translate(-50%, -50%)',
//                                     'background-color': '#D4EDDA',
//                                     'padding': '20px',
//                                     'border-radius': '10px',
//                                     'color': '#155724',
//                                     'text-align': 'center',
//                                     'z-index': '9999',
//                                     'display': 'inline-block',
//                                     'box-shadow': '0 4px 10px rgba(0, 0, 0, 0.3)', // Dark grey shadow for success box
//                                 });
//                             $('body').append($successBox);
//                             frm.refresh();
//                         }
//                     },
//                 });
//             }).css({ 'background-color': '#0F7BFE', 'color': 'white' });
//         }
//     },
// });
