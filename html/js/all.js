
// Set async flag in ajax requests
$.ajaxPrefilter(function( options, original_Options, jqXHR )
{
    options.async = true;
});

// Script communication
var xx = new CScriptLink('/_'); // , function(err) { showMessage(err, '#800'); });

// Show a message in the status bar
var msgTimeout = 0;
function showMessage(msg, col)
{
    if (!col)
        col = '#444';

    // Show the message
    $('#status')
        .html(msg).css('background', col)
        .css('display', '')
        .animate({'opacity': 1}, 1000);

    // Cancel previous timeout
    if (msgTimeout)
    {
        clearTimeout(msgTimeout);
        msgTimeout = 0;
    }

    // Restore the message after 8 seconds
    msgTimeout = setTimeout(function()
    {
        msgTimeout = 0;

        $('#status').animate(
                                {'opacity': 0},
                                1000,
                                function(){ $('#status').css('display', 'none'); }
                            );
    }, 8000);
}

// Load the folder page
$('#content').load("htm/pg/folder.html");

