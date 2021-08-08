_sai_completion() {
    COMPREPLY=( $( env COMP_WORDS="${COMP_WORDS[*]}" \
                   COMP_CWORD=$COMP_CWORD \
                   _SAI_COMPLETE=complete $1 ) )
    return 0
}

complete -F _sai_completion -o default sai;
