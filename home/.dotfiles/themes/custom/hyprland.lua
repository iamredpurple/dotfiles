local active_border_color = "rgb(241, 222, 221)"
local inactive_border_color = "rgb(26, 17, 17)"

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
