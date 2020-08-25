var dialer = {
    dial: function(opts) {
        jQuery.get(
            '/crm/util/dial/' + opts.to_number + '/',
            function (data) {
                if (data.redirect) {
                    window.location.href = data.redirect;
                    return false;
                }
                if (!data.success) {
                    alert(data.message);
                }
            });
    },

    /**
     * Send an SMS message.
     * 
     * opts.to_telephone = recipient's telephone number
     * opts.message = message to send
     * opts.before_send = callback before queuing message.
     * opts.after_send = callback after successful send
     *                   message from server passed as first arg
     */
    send_message: function(opts) {
    var telephone = encodeURIComponent(opts.to_number);
    var message = encodeURIComponent(opts.message);
    opts.before_send();
    jQuery.get(
        '/crm/util/send_message/' + telephone + '/' + message + '/',
        function (data) {
            if (data.redirect) {
                window.location.href = data.redirect;
                return false;
            }
            opts.after_send(data.message);
        });
    }

}