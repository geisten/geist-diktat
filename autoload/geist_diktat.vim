let s:generation = 0
let s:session = {}
function! s:Warn(text) abort
  echohl WarningMsg | echom 'geist-diktat: '.a:text | echohl None
endfunction
function! s:Valid(g) abort
  return !empty(s:session) && s:generation == a:g
endfunction
function! s:Flush(g, ...) abort
  if !s:Valid(a:g) || mode() =~# '^c' | return | endif
  if bufnr('%') != s:session.buffer || !bufexists(s:session.buffer)
    if !empty(s:session.queue) | call s:Warn('target buffer changed; pending text discarded') | endif
    let s:session.queue = [] | return
  endif
  let queue = s:session.queue | let s:session.queue = []
  for text in queue
    if !&l:modifiable | call s:Warn('buffer is not modifiable; text: '.text) | continue | endif
    let line = getline('.')
    let byte = col('.')-1
    if mode() !~# '^i' && strlen(line)>0
      let byte += strlen(matchstr(strpart(line,byte),'^.'))
    endif
    let text .= get(g:,'geist_diktat_suffix',' ')
    call setline('.',strpart(line,0,byte).text.strpart(line,byte))
    call cursor(line('.'),byte+strlen(text))
  endfor
endfunction
function! s:Queue(g, text) abort
  if !s:Valid(a:g) || empty(a:text) | return | endif
  if strlen(join(s:session.queue,''))+strlen(a:text)>65536
    call s:Warn('pending text limit exceeded') | call geist_diktat#stop() | return
  endif
  call add(s:session.queue,a:text)
  call timer_start(0,function('s:Flush',[a:g]))
endfunction
function! s:Out(g, channel, data) abort
  if !s:Valid(a:g) | return | endif
  let s:session.partial .= a:data
  if strlen(s:session.partial)>65536
    call s:Warn('oversized transcript') | call geist_diktat#stop() | return
  endif
  let lines = split(s:session.partial,"\n",1)
  let s:session.partial = remove(lines,-1)
  for line in lines | call s:Queue(a:g,substitute(line,'\r$','','')) | endfor
endfunction
function! s:Error(g, channel, text) abort
  if s:Valid(a:g) && a:text =~# '\(failed\|overload:\)'
    call s:Warn(a:text)
  endif
endfunction
function! s:Close(g, channel) abort
  if s:Valid(a:g)
    call s:Queue(a:g,s:session.partial) | let s:session.partial = ''
  endif
endfunction
function! s:Exit(g, job, status) abort
  if s:Valid(a:g) && a:status != 0 | call s:Warn('pipeline exited ('.a:status.')') | endif
endfunction
function! geist_diktat#active() abort
  return !empty(s:session) && has_key(s:session,'job') && job_status(s:session.job)==# 'run'
endfunction
function! geist_diktat#start() abort
  if geist_diktat#active() | return | endif
  if !has('job') || !has('channel') || !has('timers') | call s:Warn('Vim needs +job +channel +timers') | return | endif
  let s:generation += 1
  let s:session = {'partial':'','queue':[],'buffer':bufnr('%')}
  let command = get(g:,'geist_diktat_command',['geist-diktat','run'])
  if type(command)==v:t_string | let command=['sh','-c',command] | endif
  let s:session.job = job_start(command,{'out_mode':'raw','out_cb':function('s:Out',[s:generation]),
        \ 'err_cb':function('s:Error',[s:generation]),'close_cb':function('s:Close',[s:generation]),
        \ 'exit_cb':function('s:Exit',[s:generation])})
  if job_status(s:session.job)==# 'fail' | call s:Warn('could not start launcher') | endif
  augroup GeistDiktatVim
    autocmd!
    autocmd CmdlineLeave * call timer_start(0,function('s:Flush',[s:generation]))
    autocmd VimLeavePre * call geist_diktat#stop()
  augroup END
endfunction
function! geist_diktat#stop() abort
  let old = s:session | let s:session = {} | let s:generation += 1
  if has_key(old,'job') && job_status(old.job)==# 'run' | call job_stop(old.job,'term') | endif
endfunction
function! geist_diktat#toggle() abort
  if geist_diktat#active() | call geist_diktat#stop() | else | call geist_diktat#start() | endif
endfunction
