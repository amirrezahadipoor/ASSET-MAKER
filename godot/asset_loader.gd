@tool
## ASSET MAKER — Godot 4 loader
##
## Builds a Skeleton2D/Sprite2D scene from an assetmaker manifest.json:
##   - one Sprite2D per rig part, parented under its Bone2D
##   - Bone2D hierarchy from the manifest bone list (rest poses from pos/rot)
##   - AnimationPlayer clips from the manifest animations (bone rotations)
##
## Usage:
##   var scene = AssetLoader.load_asset("res://assets/animal_chicken_v01_s42")
##   add_child(scene)
##
## The folder must contain manifest.json and its PNG layers. Part PNGs are
## full-size layers; the rig recomposition equals the `full` image exactly.
class_name AssetLoader
extends RefCounted


static func load_asset(dir_path: String) -> Node2D:
	var manifest_path := dir_path.path_join("manifest.json")
	if not FileAccess.file_exists(manifest_path):
		push_error("AssetLoader: missing manifest at %s" % manifest_path)
		return null
	var manifest := _read_json(manifest_path)
	if manifest.is_empty():
		return null

	var size: Array = manifest.get("size", [0, 0])
	var anchor: Array = manifest.get("anchor", [0, 0])
	var root := Node2D.new()
	root.name = String(manifest.get("id", "asset"))
	# manifest space -> Godot space: anchor becomes the origin
	root.set_meta("asset_size", Vector2(size[0], size[1]))
	root.set_meta("asset_anchor", Vector2(anchor[0], anchor[1]))

	var rig: Dictionary = manifest.get("rig", {})
	var files: Dictionary = manifest.get("files", {})

	# shadow layer first (bottom), full-canvas sprite
	var shadow_file: String = files.get("shadow", "")
	if shadow_file != "":
		var sh := _make_layer_sprite(dir_path, shadow_file, size, anchor)
		sh.name = "Shadow"
		sh.z_index = -100
		root.add_child(sh)

	if rig.is_empty():
		# static asset: single full sprite
		var full := _make_layer_sprite(dir_path, files.get("full", ""), size, anchor)
		full.name = "Full"
		root.add_child(full)
		return root

	# ---- skeleton ----
	var skeleton := Skeleton2D.new()
	skeleton.name = "Skeleton2D"
	root.add_child(skeleton)
	var bone_nodes := {}
	var bones: Array = rig.get("bones", [])
	for b in bones:
		var bone := Bone2D.new()
		var bname: String = b["name"]
		bone.name = bname
		bone_nodes[bname] = bone
		var pos: Array = b["pos"]
		var parent_name = b.get("parent")
		if parent_name != null and bone_nodes.has(parent_name):
			var parent: Bone2D = bone_nodes[parent_name]
			parent.add_child(bone)
			# bone positions in manifest are asset-space; convert to local
			var ppos: Array = _bone(bones, parent_name)["pos"]
			bone.position = Vector2(pos[0] - ppos[0], pos[1] - ppos[1])
		else:
			skeleton.add_child(bone)
			bone.position = Vector2(pos[0] - anchor[0], pos[1] - anchor[1])
		bone.rotation_degrees = float(b.get("rot", 0.0))
		bone.set_meta("rest_rotation", bone.rotation_degrees)

	# ---- parts as sprites on bones ----
	var parts: Array = rig.get("parts", [])
	for p in parts:
		var sprite := _make_layer_sprite(dir_path, p["file"], size, anchor)
		sprite.name = "Part_" + String(p["name"])
		sprite.z_index = int(p.get("z", 0))
		var bone_name: String = p["bone"]
		if bone_nodes.has(bone_name):
			var bone: Bone2D = bone_nodes[bone_name]
			bone.add_child(sprite)
			# keep the sprite in asset space: undo the bone's offset
			var bpos: Array = _bone(bones, bone_name)["pos"]
			sprite.position = Vector2(anchor[0] - bpos[0], anchor[1] - bpos[1])
		else:
			root.add_child(sprite)

	# ---- animations ----
	var animations: Dictionary = rig.get("animations", {})
	if not animations.is_empty():
		_build_animation_player(root, bone_nodes, animations)
	return root


static func _read_json(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return {}
	var parsed = JSON.parse_string(f.get_as_text())
	if parsed is Dictionary:
		return parsed
	return {}


static func _bone(bones: Array, bone_name: String) -> Dictionary:
	for b in bones:
		if String(b["name"]) == bone_name:
			return b
	return {}


static func _make_layer_sprite(dir_path: String, file_name: String,
		size: Array, anchor: Array) -> Sprite2D:
	var sprite := Sprite2D.new()
	var tex := load(dir_path.path_join(file_name)) as Texture2D
	if tex == null:
		var img := Image.load_from_file(dir_path.path_join(file_name))
		if img != null:
			tex = ImageTexture.create_from_image(img)
	sprite.texture = tex
	sprite.centered = true
	# layer PNGs are full-size; position so the texture maps 1:1 on the asset
	sprite.position = Vector2(size[0] * 0.5 - anchor[0], size[1] * 0.5 - anchor[1])
	sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	return sprite


static func _build_animation_player(root: Node2D, bone_nodes: Dictionary,
		animations: Dictionary) -> void:
	var player := AnimationPlayer.new()
	player.name = "AnimationPlayer"
	root.add_child(player)
	var library := AnimationLibrary.new()
	for anim_name in animations:
		var anim: Dictionary = animations[anim_name]
		var clip := Animation.new()
		var frames: Array = anim.get("frames", [])
		var fps := float(anim.get("fps", 6.0))
		var length := float(frames.size()) / fps
		clip.length = max(length, 0.01)
		clip.loop_mode = Animation.LOOP_LINEAR if anim.get("loop", true) \
				else Animation.LOOP_NONE
		for bone_name in bone_nodes:
			var track := clip.add_track(Animation.TYPE_VALUE)
			var node_path := NodePath("Skeleton2D/" + String(bone_name)
					+ ":rotation_degrees")
			clip.track_set_path(track, node_path)
			clip.track_set_interpolation_type(track,
					Animation.INTERPOLATION_NEAREST)
		for i in range(frames.size()):
			var frame: Dictionary = frames[i]
			var t := float(i) / fps
			var rots: Dictionary = frame.get("bones", {})
			for bone_name in bone_nodes:
				var rest := 0.0
				var bone: Bone2D = bone_nodes[bone_name]
				if bone.has_meta("rest_rotation"):
					rest = float(bone.get_meta("rest_rotation"))
				var rot := rest + float(rots.get(bone_name, 0.0))
				var track := _find_track(clip, String(bone_name))
				if track >= 0:
					clip.track_insert_key(track, t, rot)
		library.add_animation(String(anim_name), clip)
	if not library.get_animation_list().is_empty():
		player.add_animation_library("", library)


static func _find_track(clip: Animation, bone_name: String) -> int:
	var suffix := bone_name + ":rotation_degrees"
	for i in range(clip.get_track_count()):
		var path := String(clip.track_get_path(i))
		if path.ends_with(suffix):
			return i
	return -1
