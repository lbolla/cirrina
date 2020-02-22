"""
`cirrina` - Opinionated web framework

Simple cirrina server example.

:license: LGPL, see LICENSE for details
"""

import logging
import sys
import cirrina

from aiohttp import web

#: Holds the login html template
LOGIN_HTML = '''<!DOCTYPE HTML>
<html>
  <body>
    <div style="max-width:350px; margin:auto; text-align:right;">
      <h1 style="text-align:left;">Login</h1>
      <form id="loginForm" method="post">
        Username: <input type="text" name="username"><br/>
        Password: <input type="password" name="password"><br/>
        <input type="hidden" name="path" value="{0}">
        <button type="button" onclick="login()">Login</button>
      </form>
    </div>
    <script>
    function login()
    {{
        var form = document.getElementById('loginForm');
        var form_data = new FormData(form);
        var http = new XMLHttpRequest();
        http.open('POST', '/login', true);
        http.addEventListener('load', function(event) {{
           if (http.status >= 200 && http.status < 300) {{
              window.location = "/";
           }} else {{
              alert('Authentication failed !');
           }}
        }});
        http.send(form_data);
    }}
    </script>
  </body>
</html>
'''


#: Holds the logger for the current example
logger = logging.getLogger(__name__)

#: Create cirrina app.
app = cirrina.Server()
app.http_static("/static", cirrina.Server.DEFAULT_STATIC_PATH)
app.enable_rpc('/jrpc')
wspath = '/ws'


@app.auth_handler
async def auth_handler(request, username, password):
    if username == 'admin' and password == 'admin':
        return True
    return False


@app.websocket_connect()
async def websocket_connected(wsclient):
    username = wsclient.cirrina.web_session['username']
    logger.info("websocket: new authenticated connection, user: %s", username)


@app.websocket_message(location=wspath)
async def websocket_message(wsclient, msg):
    logger.info("websocket: got message: '%s'", msg)
    app.websocket_broadcast(msg)


@app.websocket_disconnect()
async def websocket_closed(wsclient):
    logger.info('websocket connection closed')


@app.http_get('/login')
async def _login(request):
    """
    Send login page to client.
    """
    return web.Response(text=LOGIN_HTML.format(request.get('path', "/")), content_type="text/html")


@app.http_get('/')
@app.authenticated
async def default(request):
    """
    ---
    description: This is the default page
    tags:
    - Defaulty Default
    produces:
    - text/html
    responses:
        "200":
            description: successful operation.
        "405":
            description: invalid HTTP Method
    """

    visit_count = 0
    if 'visit_count' in request.cirrina.web_session:
        visit_count = request.cirrina.web_session['visit_count']
    request.cirrina.web_session['visit_count'] = visit_count + 1

    html = '''<!DOCTYPE HTML>
<html>
<head>
<script type="text/javascript" src="static/cirrina.js"></script>
<script type="text/javascript">
  function log( msg )
  {
    document.body.innerHTML += msg + "<br/>";
    /*alert( msg );*/
  }
  var cirrina = new Cirrina('%s');

  cirrina.onopen = function(ws)
  {
    log("connected" );
    msg = "Hello"
    log("send: " + msg );
    ws.send( msg );
  };
  cirrina.onmessage = function (ws, msg)
  {
    log("got: " + msg );
  };
  cirrina.onclose = function()
  {
    log("disconnected");
  };
</script>
</head>
<body>
 <input type="text" id="text">
 <input type='button' value='Send' onclick="cirrina.send(document.getElementById('text').value);">
 visit count: %d <br/>
 <br/>
 <form id="upload" action="/upload" method="post" accept-charset="utf-8" enctype="multipart/form-data">
    <label for="file">File Upload</label>
    <input id="file" name="file" type="file" value="" />
    <input type="button" value="submit" onclick="form.submit();"/>
 </form>
</body>
</html>
''' % (wspath, visit_count)
    resp = web.Response(text=html, content_type="text/html")
    return resp


@app.jrpc
async def hello(request, session, msg, n, debug=False):
    logger.info("jrpc hello called: %s - %d, debug: %d", msg, n, debug)
    visit_count = session['visit_count'] if 'visit_count' in session else 1
    session['visit_count'] = visit_count + 1
    app.websocket_broadcast(msg)
    return {"status": msg, 'visit_count': visit_count - 1}


@app.startup
def onstart():
    logger.info("starting up...")


@app.shutdown
def onstop():
    logger.info("shutting down...")


@app.http_upload('/upload', upload_dir="upload/")
async def file_upload(request, session, upload_die, filename, size):
    return web.Response(text='file uploaded: {} ({} bytes)'.format(filename, size))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    port = 8765
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    app.run('0.0.0.0', port, debug=True)
