import io
from PIL import Image, ImageDraw, ImageFont
import psutil
import time
import requests
from typing import Tuple, NamedTuple

# Constants
IMAGE_WIDTH = 240
IMAGE_HEIGHT = 240
IMAGE_FILENAME = "system_info.jpg"
FONT_SIZE = 28
FONT_PATH = "ZenMaruGothic-Regular.ttf"
BACKGROUND_COLOR = "black"
TEXT_COLOR = "white"
UPDATE_INTERVAL = 0  # seconds
DEVICE_IP = "192.168.0.19"

# 追加の定数
ICON_SIZE = 40
ICON_CUSTOM_SIZE = 80
ICON_MARGIN = 10
ICON_POSITIONS = {
    "cpu": (IMAGE_WIDTH - ICON_SIZE - ICON_MARGIN, ICON_MARGIN),
    "ram": (IMAGE_WIDTH - ICON_SIZE - ICON_MARGIN, 2 * ICON_MARGIN + ICON_SIZE),
    "custom": (IMAGE_WIDTH - ICON_CUSTOM_SIZE - ICON_MARGIN, ICON_MARGIN),
}
ICON_COLORS = ["green", "lightgreen", "yellow", "orange", "red"]
ICON_IMAGES = ["assets/lv_1.jpg", "assets/lv_2.jpg", "assets/lv_3.jpg", "assets/lv_4.jpg", "assets/lv_5.jpg"]
ICON_LOADED_IMAGES = [Image.open(f) for f in ICON_IMAGES]


def get_icon_color(usage: float) -> str:
    """Get the color of the icon based on usage percentage."""
    if usage < 20:
        return ICON_COLORS[0]
    elif usage < 40:
        return ICON_COLORS[1]
    elif usage < 60:
        return ICON_COLORS[2]
    elif usage < 80:
        return ICON_COLORS[3]
    else:
        return ICON_COLORS[4]


def get_icon_image(usage: float) -> Image.Image:
    """Get the image of the icon based on usage percentage."""
    if usage < 20:
        return ICON_LOADED_IMAGES[0]
    elif usage < 40:
        return ICON_LOADED_IMAGES[1]
    elif usage < 60:
        return ICON_LOADED_IMAGES[2]
    elif usage < 80:
        return ICON_LOADED_IMAGES[3]
    else:
        return ICON_LOADED_IMAGES[4]


def draw_usage_icon(
    draw: ImageDraw.ImageDraw, position: Tuple[int, int], usage: float, label: str
) -> None:
    """Draw a usage icon with the given color and label."""
    color = get_icon_color(usage)
    draw.ellipse(
        [position, (position[0] + ICON_SIZE, position[1] + ICON_SIZE)], fill=color
    )
    font = get_font(size=16)
    draw.text(
        (position[0] + ICON_SIZE // 2, position[1] + ICON_SIZE // 2),
        label,
        fill="black",
        font=font,
        anchor="mm",
    )


def paste_usage_custom_icon(
    base_image: Image.Image,
    position: Tuple[int, int],
    usage: float,
) -> None:
    """Paste the icon image onto the base image."""
    img = get_icon_image(usage)
    img = img.resize((ICON_CUSTOM_SIZE, ICON_CUSTOM_SIZE))
    base_image.paste(img, position, img if img.mode == 'RGBA' else None)


def format_transfer_speed(speed_bytes: float) -> str:
    """Format transfer speed in appropriate units (MB/s or KB/s)."""
    if speed_bytes >= 1024 * 1024:  # 1 MB/s以上の場合
        return f"{speed_bytes / (1024 * 1024):.2f} MB/s"
    else:
        return f"{speed_bytes / 1024:.2f} KB/s"


class SystemInfo(NamedTuple):
    cpu_usage: float
    ram_usage: float
    net_send: float
    net_recv: float


def get_system_info() -> SystemInfo:
    """Collect system information."""
    cpu_usage = psutil.cpu_percent(interval=1)
    ram_usage = psutil.virtual_memory().percent

    network_stats_before = psutil.net_io_counters()
    time.sleep(1)
    network_stats_after = psutil.net_io_counters()

    transfer_speed_sent = (
        network_stats_after.bytes_sent - network_stats_before.bytes_sent
    )
    transfer_speed_recv = (
        network_stats_after.bytes_recv - network_stats_before.bytes_recv
    )

    return SystemInfo(cpu_usage, ram_usage, transfer_speed_sent, transfer_speed_recv)


def get_font(size: int = FONT_SIZE) -> ImageFont.FreeTypeFont:
    """Get the font for drawing text."""
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except IOError:
        return ImageFont.load_default()


def create_info_image(info: SystemInfo) -> Image.Image:
    """Create an image with system information."""
    image = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)
    font = get_font()

    send_speed = format_transfer_speed(info.net_send)
    recv_speed = format_transfer_speed(info.net_recv)

    text = (
        "智乃モニタ\n\n"
        f"CPU: {info.cpu_usage:.1f}%\n"
        f"RAM: {info.ram_usage:.1f}%\n"
        f"Send: {send_speed}\n"
        f"Recv: {recv_speed}"
    )
    draw.text((10, 10), text, fill=TEXT_COLOR, font=font)

    target_usage = info.cpu_usage if info.cpu_usage > info.ram_usage else info.ram_usage

    paste_usage_custom_icon(
        image, ICON_POSITIONS["custom"], target_usage
    )

    # CPU使用率アイコンの描画
    # draw_usage_icon(draw, ICON_POSITIONS["cpu"], info.cpu_usage, "CPU")
    # RAM使用率アイコンの描画
    # draw_usage_icon(draw, ICON_POSITIONS["ram"], info.ram_usage, "RAM")

    return image


def save_image(image: Image.Image, filename: str) -> None:
    """Save the image to a file."""
    image.save(filename)


def save_image_to_bytes(image: Image.Image) -> io.BytesIO:
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format="JPEG")
    img_byte_arr.seek(0)
    return img_byte_arr


def upload_image_to_device_by_file(filename: str) -> bool:
    """Upload the image to the device."""
    url = f"http://{DEVICE_IP}/doUpload?dir=/image/"
    with open(filename, "rb") as file:
        files = {"file": ("image.jpg", file, "image/jpeg")}
        try:
            response = requests.post(url, files=files)
            # InvalidHeaderエラーが発生しても処理を続行
        except requests.exceptions.InvalidHeader:
            print("InvalidHeader例外が発生しましたが、正常として処理を続行します。")
            return True  # エラーを無視して成功したものとして扱う
    if response.status_code == 200:
        print("Image successfully uploaded to the device.")
        return True
    else:
        print(
            f"Error uploading the image to the device. Status code: {response.status_code}"
        )
        return False


def upload_image_to_device_by_bytes(image_bytes: io.BytesIO):
    url = f"http://{DEVICE_IP}/doUpload?dir=/image/"
    files = {"file": ("image.jpg", image_bytes, "image/jpeg")}
    try:
        response = requests.post(url, files=files)
        if response.status_code == 200:
            print("Image successfully uploaded to the device.")
            return True
        else:
            print(
                f"Error uploading the image to the device. Status code: {response.status_code}"
            )
            return False
    except requests.exceptions.InvalidHeader:
        print("InvalidHeader例外が発生しましたが、正常として処理を続行します。")
        return True  # エラーを無視して成功したものとして扱う
    except requests.exceptions.RequestException as e:
        print(f"Error during upload: {e}")
        return False


def set_image_on_device(image_name: str) -> bool:
    """Set the image on the device."""
    url = f"http://{DEVICE_IP}/set?img=%2Fimage%2F{image_name}"
    response = requests.get(url)
    if response.status_code == 200:
        print("Image successfully set on the device.")
        return True
    else:
        print(
            f"Error setting the image on the device. Status code: {response.status_code}"
        )
        return False


def update_device_display() -> None:
    """Update the device display with current system information."""
    info = get_system_info()
    info_image = create_info_image(info)
    image_bytes = save_image_to_bytes(info_image)
    # save_image(info_image, IMAGE_FILENAME)
    if upload_image_to_device_by_bytes(image_bytes):
        set_image_on_device(IMAGE_FILENAME)


def main() -> None:
    """Main function to run the program."""
    while True:
        update_device_display()
        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()
