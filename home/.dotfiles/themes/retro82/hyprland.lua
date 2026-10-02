hl.config({
	general = {
		col = {
			active_border = "rgb(faa96d)",
		},
	},

	decoration = {
		blur = {
			enabled = false,
		},
		active_opacity = 0.95,
		inactive_opacity = 0.90,
	},
})

hl.layer_rule({
	match = { namespace = "waybar" },
	blur = false,
	ignore_alpha = 0.1,
})

hl.layer_rule({
	match = { namespace = "notifications" },
	blur = false,
	ignore_alpha = 0.1,
})

hl.layer_rule({
	match = { namespace = "walker" },
	blur = false,
	ignore_alpha = 0.1,
})
