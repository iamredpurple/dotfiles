Name = "theme_switcher"
NamePretty = "Theme Switcher"
Icon = "" --"preferences-desktop-theme"
Cache = false

Action = os.getenv("HOME") .. "/.local/bin/theme-change %VALUE%"

local function file_exists(path)
	local f = io.open(path, "r")
	if f then
		f:close()
		return true
	else
		return false
	end
end

function GetEntries()
	local entries = {}
	local theme_dir = os.getenv("HOME") .. "/.dotfiles/themes/"

	local p = io.popen("ls -d " .. theme_dir .. "*/ 2>/dev/null")
	if not p then
		return entries
	end

	for line in p:lines() do
		local theme_name = line:match("([^/]+)/$")

		if theme_name then
			local preview_path = theme_dir .. theme_name .. "/preview.png"
			local item_icon = "preferences-desktop-theme"

			if file_exists(preview_path) then
				item_icon = preview_path
			end

			table.insert(entries, {
				Text = theme_name:lower():gsub("^%l", string.upper),
				Subtext = "Apply " .. theme_name .. " theme",
				Preview = preview_path,
				Icon = "",
				Value = theme_name,
			})
		end
	end
	p:close()

	return entries
end
