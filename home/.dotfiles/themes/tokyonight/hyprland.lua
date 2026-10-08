hl.config({
	general = {
		gaps_in = 2,
		gaps_out = 3,
		col = {
			active_border = "rgb(7aa2f7)",
		},
	},

	decoration = {
		rounding = 10,
		rounding_power = 2,
		active_opacity = 0.9,
		inactive_opacity = 0.85,
		shadow = {
			enabled = true,
			range = 12,
			render_power = 4,
			color = "rgb(7aa2f7)",
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

hl.layer_rule({
	match = { namespace = "walker" },
	blur = true,
	ignore_alpha = 0.1,
})

hl.layer_rule({
	match = { namespace = "swayosd" },
	blur = true,
	ignore_alpha = 0.1,
})
