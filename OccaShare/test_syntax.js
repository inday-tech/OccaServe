try {
    eval(new ActiveXObject('Scripting.FileSystemObject').OpenTextFile('app/static/js/caterer/calendar.js', 1).ReadAll());
    WScript.Echo('Syntax OK (but execution failed as expected, or passed)');
} catch (e) {
    WScript.Echo('Error: ' + e.name + ' - ' + e.message + ' (Line: ' + (e.line || 'unknown') + ')');
}
