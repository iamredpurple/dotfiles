local active_border_color = "rgb(193, 196, 151)"
local inactive_border_color = "rgb(17, 28, 24)"

hl.config({
	general = {
		gaps_in = 2,
		gaps_out = 3,
		col = {
			active_border = active_border_color,
			inactive_border = inactive_border_color,
		},
	},
	decoration = {
		rounding = 10,
		rounding_power = 2,
		active_opacity = 0.90,
		inactive_opacity = 0.86,
		shadow = {
			enabled = true,
			range = 12,
			render_power = 4,
			color = active_border_color,
			color_inactive = "rgba(30486077)",
		},
	},
})

hl.window_rule({
	match = { class = "^(chromasdf.*)$" },
	no_blur = true,
	opaque = true,
})

hl.layer_rule({
	match = { namespace = "waybar" },
	blur = true,
	ignore_alpha = 0.1,
})

hl.layer_rule({
	match = { namespace = "notifications" },
	blur = true,
	ignore_alpha = 0.1,
})

-- hl.layer_rule({
-- 	match = { namespace = "walker" },
-- 	blur = true,
-- 	ignore_alpha = 0.1,
-- })

hl.layer_rule({
	match = { namespace = "swayosd" },
	blur = true,
	ignore_alpha = 0.1,
})
