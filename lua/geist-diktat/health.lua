-- :checkhealth geist-diktat
local M = {}

function M.check()
    local health = vim.health
    health.start("geist-diktat")

    local diktat = require("geist-diktat")
    local binary = vim.fn.exepath(diktat.opts.binary)
    if binary ~= "" then
        health.ok("diktat binary: " .. binary)
    else
        health.warn(diktat.opts.binary .. " not found — set setup({ binary = ... }) or install the .deb")
    end

    if vim.fn.executable("arecord") == 1 then
        health.ok("arecord found")
    else
        health.error("arecord missing (apt install alsa-utils)")
    end

    local model = diktat.opts.model
    if vim.fn.filereadable(model) == 1 then
        health.ok("model: " .. model)
    else
        health.warn("model missing — run: geist-diktat setup (or set setup({ model = ... }))")
    end

    if diktat.is_active() then
        health.info("currently listening")
    end
end

return M
