/**

    CScriptLink()

    Class implementing a queued ajax object

*/
function CScriptLink(link, fError, timeout = 8000)
{
    var cb = {};
    var queue = [];
    var inreq = 0;
    var pqueue = {};
    var timer = 0;

    // Queue message for sending
    function msg(cmd, params, cb)
    {
        queue.push({'c': cmd, 'p': params, 'f': cb});
        send_cmds()
    }

    // Add a polling entry
    function pmsg(name, to, cmd, params, cb)
    {
        var now = (new Date()).getTime();
        pqueue[name] = {'t': now + to, 'to': Math.abs(to), 'c': cmd, 'p': params, 'f': cb};
        send_cmds()
    }

    // Modify a polling entry
    function modify_pmsg(name, p, refresh)
    {
        if (!(name in pqueue))
            return;

        if (p['to'])
            pqueue[name]['to'] = p['to'];
        if (p['cmd'])
            pqueue[name]['c'] = p['cmd'];
        if (p['params'])
            pqueue[name]['p'] = p['params'];
        if (p['cb'])
            pqueue[name]['f'] = p['cb'];

        if (refresh)
        {
            pqueue[name]['t'] = 0;
            send_cmds();
        }
    }

    // Remove a polling entry
    function remove_pmsg(name)
    {
        if (name in pqueue)
            delete pqueue[name];
    }

    // Send queued commands
    function send_cmds()
    {
        // Are we in queue?
        if (inreq)
            return;

        // Clear any timer callback that may be out there
        if (timer)
        {
            clearTimeout(timer);
            timer = 0;
        }

        // Do we need to run?
        if(!queue.length && !Object.keys(pqueue).length)
            return;

        cb = {};

        var c = 0, cmds = {};
        var now = (new Date()).getTime();

        // One shot commands
        $.each(queue, function(k, v)
        {
            // Save callback
            cb[c] = { 'f': v['f'] };

            // Build cmd string
            cmds[c] = {'c': v['c'], '_': v['p']};

            c++;
        });

        // Clear the queue
        queue = [];

        // Polling commands
        $.each(pqueue, function(k, v)
        {
            // Is it time to poll?
            if (v['t'] > now)
                return true;

            // Set next timeout
            v['t'] = now + Math.abs(v['to']);

            // Save callback
            cb[c] = {'k': k, 'f': v['f']};

            // Build cmd string
            cmds[c] = {'c': v['c'], '_': v['p']};

            c++
        });

        // Did we get anything to send?
        if (!Object.keys(cmds).length)
        {
            // We're done if not polling
            if (!Object.keys(pqueue).length)
                return;

            // Set a timer for the polling
            timer = setTimeout(function() { timer = 0; send_cmds(); }, 1000);

            return;
        }

        // We're processing
        inreq = 1;

        // Send the request
        $.ajax({

            'url': link,
            'dataType': "json",
            'timeout': timeout,
            'data': {'cmds': JSON.stringify(cmds)},

            'success': function(data)
            {
                $.each(data, function(k, v)
                {
                    if (k in cb)
                    {
                        // Global error handler?
                        if (fError)
                            if ('error' in v)
                                fError(v['error'], v);

                        // Execute callback
                        var r = cb[k]['f'](1, v);

                        // Remove polling if callback returned false
                        if (!r && 'k' in cb[k])
                            remove_pmsg(cb[k]['k']);

                        // Remove callback from list
                        delete cb[k];
                    }
                });

                $.each(cb, function(k, v)
                {
                    if (fError)
                        fError('Response not received');

                    // Execute callback
                    var r = v['f'](0, {'error': 'Response not received'});

                    // Remove polling if callback returned false
                    if (!r && 'k' in v[k])
                        remove_pmsg(v['k']);
                });

                cb = {};
                inreq = 0;
                send_cmds();
            },

            'error': function(xhr, txt, err)
            {
                console.log(xhr.responseText + " : " + txt + " : " + err);

                if (fError)
                    fError(txt, err);

                $.each(cb, function(k, v)
                {
                    if (txt !== err)
                        txt += " : " + err;

                    // Execute callback
                    var r = v['f'](0, {'error': 'Request Error: ' + txt});

                    // Remove polling if callback returned false
                    if (!r && 'k' in v[k])
                        remove_pmsg(v['k']);
                });

                cb = {};
                inreq = 0;
                send_cmds();
            }
        });

    }

    // Export
    this.msg = msg;
    this.pmsg = pmsg;
    this.remove_pmsg = remove_pmsg;
    this.modify_pmsg = modify_pmsg;
}
