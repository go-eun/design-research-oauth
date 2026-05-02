import Quartz
window_list = Quartz.CGWindowListCopyWindowInfo(
    Quartz.kCGWindowListOptionOnScreenOnly,
    Quartz.kCGNullWindowID
)
for w in window_list:
    owner = w.get('kCGWindowOwnerName', '')
    name  = w.get('kCGWindowName', '')
    if owner and name:
        print(f"owner: {owner:<30} | name: {name}")
