hl.config({
	general = {
		gaps_in = 2,
		gaps_out = 2,
		border_size = 2,
		col = {
			active_border = "rgb(d3c6aa)",
		},
	},

	decoration = {
		active_opacity = 0.95,
		inactive_opacity = 0.94,
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
