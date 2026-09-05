if vim.g.loaded_geist_diktat then return end
vim.g.loaded_geist_diktat = true
for name, method in pairs({Diktat='toggle', DiktatToggle='toggle', DiktatStart='start', DiktatStop='stop'}) do
    vim.api.nvim_create_user_command(name, function() require('geist-diktat')[method]() end, {})
end
vim.keymap.set({'n','i'}, '<Plug>(DiktatToggle)', function() require('geist-diktat').toggle() end)
