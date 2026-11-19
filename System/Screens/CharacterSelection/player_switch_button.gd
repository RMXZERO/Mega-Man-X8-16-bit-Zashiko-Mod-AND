extends X8TextureButton

# 캐릭터 선택 화면 좌우 화살표 터치 버튼 (Android/모바일용)
# - 버튼은 투명하게 두고(self_modulate) 화면에 보이는 화살표 위에 겹쳐서 터치만 받는다.
# - 키보드/게임패드 포커스를 가져가지 않도록 포커스는 항상 NONE 으로 유지한다.

onready var char_container = $"../characters/panel/char_container"
export  var direction = "right"

func on_start() -> void :
	pass

func enable() -> void :
	# 부모(X8TextureButton)는 FOCUS_ALL 로 되돌리지만, 이 버튼은 포커스를 받지 않는다
	focus_mode = Control.FOCUS_NONE

func _on_focus_entered() -> void :
	pass

func _on_focus_exited() -> void :
	pass

func _on_mouse_entered() -> void :
	pass

func _on_pressed() -> void :
	# 시작 버튼을 눌러 화면이 잠긴 뒤에는 무시
	if menu and menu.locked:
		return
	on_press()

func on_press() -> void :
	char_container.emit_signal("switch_character", direction)
	_flash_arrow()

func _flash_arrow() -> void :
	# 눌렀을 때 눈에 보이는 화살표를 잠깐 밝게
	var arrow = get_node_or_null("../Menu_Frame/" + name)
	if arrow:
		arrow.modulate = Color(3, 3, 3, 1)
		create_tween().tween_property(arrow, "modulate", Color(1, 1, 1, 1), 0.2)
