regex = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'

is_initialized = False
prototxt = None
caffemodel = None
net = None
# webserver = "http://insite.ngrok.io"
webserver = "https://insite.vn"

WINDOW_LOGO = 0
ERROR_LOGO = 1
SUCCESS_LOGO = 2
DENIED_LOGO = 3

LOGIN_SCREEN = "login"
WEBCAM_SCREEN = "webcam"
REGISTER_SCREEN = "register"