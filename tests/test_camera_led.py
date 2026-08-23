from app import camera_led


def test_virtual_led_control_maps_native_off_to_gui_off():
    control = camera_led._virtual_control({"led_native_value": 0})
    assert control["name"] == "Kamera_LED"
    assert control["type"] == "bool"
    assert control["value"] == 0
    assert control["writable"] is True


def test_virtual_led_control_maps_auto_to_gui_on():
    control = camera_led._virtual_control({"led_native_value": 3})
    assert control["value"] == 1


def test_non_logitech_without_led_control_is_not_advertised(monkeypatch):
    monkeypatch.setattr(camera_led, "_usb_identity", lambda device: {
        "usb_vendor_id": "1234",
        "usb_product_id": "5678",
        "usb_device_revision": "0100",
        "firmware_revision": "0100",
        "usb_product": "Generic UVC Camera",
    })
    monkeypatch.setattr(camera_led, "_parse_v4l2_led_control", lambda device: None)
    monkeypatch.setattr(camera_led, "_uvcdynctrl_led_control", lambda device: None)
    cap = camera_led._capability("/dev/video0", {"name": "Generic UVC Camera"})
    assert cap["led_supported"] is False
    assert cap["firmware_revision"] == "0100"


def test_confirmed_native_led_control_is_advertised(monkeypatch):
    monkeypatch.setattr(camera_led, "_usb_identity", lambda device: {
        "usb_vendor_id": "046d",
        "usb_product_id": "082d",
        "usb_device_revision": "0011",
        "firmware_revision": "0011",
        "usb_product": "HD Pro Webcam C920",
    })
    monkeypatch.setattr(camera_led, "_parse_v4l2_led_control", lambda device: {
        "method": "v4l2",
        "native_control": "led1_mode",
        "native_value": 3,
        "writable": True,
    })
    cap = camera_led._capability("/dev/video0", {"name": "HD Pro Webcam C920", "c920_match": True})
    assert cap["c920_family"] is True
    assert cap["led_supported"] is True
    assert cap["led_method"] == "v4l2"
    assert cap["led_native_control"] == "led1_mode"
