if has('nvim') || exists('g:loaded_geist_diktat_vim') | finish | endif
let g:loaded_geist_diktat_vim = 1
command! DiktatStart call geist_diktat#start()
command! DiktatStop call geist_diktat#stop()
command! DiktatToggle call geist_diktat#toggle()
command! DiktatHealth echo system('geist-diktat doctor')
nnoremap <silent> <Plug>(DiktatToggle) :DiktatToggle<CR>
inoremap <silent> <Plug>(DiktatToggle) <C-O>:DiktatToggle<CR>
