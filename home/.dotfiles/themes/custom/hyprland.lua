local active_border_color = "rgb(224, 227, 232)"
local inactive_border_color = "rgb(16, 20, 23)"

hl.config({
  general = {
    col = {
      active_border = active_border_color,
      inactive_border = inactive_border_color,
    },
  },
  decoration = {
      active_opacity = 0.95,
      inactive_opacity = 0.90,
  },
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
