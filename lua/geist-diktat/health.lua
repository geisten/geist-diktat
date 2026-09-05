local M={}
function M.check()
  local h=vim.health
  h.start('geist-diktat')
  local d=require('geist-diktat')
  if d.opts.cmd then h.info('custom command configured; run it manually to diagnose')
  elseif vim.fn.executable(d.opts.launcher)==1 then
    h.ok('launcher: '..vim.fn.exepath(d.opts.launcher))
    local output=vim.fn.system({d.opts.launcher,'doctor'})
    if vim.v.shell_error==0 then h.ok(output) else h.error(output) end
  else h.error('launcher missing; install geist-diktat and run geist-diktat setup') end
  if d.is_active() then h.info('dictation active') end
end
return M
