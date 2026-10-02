Name = "wallpaper_switcher"
NamePretty = "Wallpaper Switcher"
Icon = ""

local function title_case(str)
	local words = {}
	for word in string.gmatch(str, "%S+") do
		local first = string.sub(word, 1, 1):upper()
		local rest = string.sub(word, 2):lower()
		table.insert(words, first .. rest)
	end
	return table.concat(words, " ")
end

local function get_files(cmd)
	local popen = io.popen(cmd)
	if not popen then
		return {}
	end
	local files = {}
	for line in popen:lines() do
		table.insert(files, line)
	end
	popen:close()
	return files
end

function GetEntries()
	local home = os.getenv("HOME")
	local wallpaper_dir = home .. "/.config/current_theme/wallpapers"
	local entries = {}

	local cmd = string.format(
		'find "%s" -type f \\( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \\) -printf "%%f\\n"',
		wallpaper_dir
	)
	local files = get_files(cmd)

	for _, filename in ipairs(files) do
		local clean_name = filename:gsub("%.[^.]+$", "")
		clean_name = clean_name:gsub("^[0-9]+%-?", "")
		clean_name = clean_name:gsub("[%-_]", " ")
		local display_name = title_case(clean_name)

		-- Absolute path to pass to the image renderer and wallpaper setter
		local full_path = wallpaper_dir .. "/" .. filename

		table.insert(entries, {
			Text = display_name,
			Subtext = "Apply " .. display_name .. " wallpaper",
			Preview = full_path,
			Actions = {
				default = string.format(
					home
						.. "/.local/bin/wallpaper "
						.. full_path
						.. ' && notify-send "󰂚 Wallpaper Changed" "Wallpaper has been changed to '
						.. "'"
						.. display_name
						.. "'"
						.. '"'
						.. " -t 2000"
				),
			},
		})
	end

	return entries
end
