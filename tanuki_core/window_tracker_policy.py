from dataclasses import dataclass


@dataclass
class WindowSurface:
    hwnd: int
    rect: object
    title: str
    class_name: str

    def perch_y(self, actor_height):
        return self.rect.top() - actor_height

    def clamp_actor_x(self, x, actor_width):
        min_x = self.rect.left()
        max_x = self.rect.left() + self.rect.width() - actor_width
        if max_x < min_x:
            return min_x
        return max(min_x, min(max_x, int(x)))

    def contains_x(self, x):
        return self.rect.left() <= int(x) <= (self.rect.left() + self.rect.width())


def build_window_surface(
    snapshot,
    *,
    own_pid,
    min_window_width,
    min_window_height,
    ws_ex_toolwindow,
    ws_child,
    ws_popup,
    ws_caption,
    excluded_classes=("Shell_TrayWnd", "Progman", "WorkerW"),
):
    if not snapshot.is_visible or snapshot.is_iconic or snapshot.is_cloaked:
        return None
    if snapshot.pid == own_pid:
        return None
    if snapshot.owner_hwnd:
        return None
    if snapshot.style & ws_child:
        return None
    if snapshot.ex_style & ws_ex_toolwindow:
        return None
    if (snapshot.style & ws_popup) and not (snapshot.style & ws_caption):
        return None
    if snapshot.class_name in excluded_classes:
        return None
    if not snapshot.title:
        return None
    if snapshot.rect.width() < min_window_width or snapshot.rect.height() < min_window_height:
        return None
    return WindowSurface(
        hwnd=int(snapshot.hwnd),
        rect=snapshot.rect,
        title=snapshot.title,
        class_name=snapshot.class_name,
    )
