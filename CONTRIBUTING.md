## GitHub Workflow

We're following basic GitHub Flow. If you have no idea what we're talking 
about, check out [GitHub's official guide](https://guides.github.com/introduction/flow/). 
Note that merge is only performed by the repository maintainer.

Guide for performing commits:

* Isolate each commit to one component/bugfix/issue/feature
* Use a standard commit message format:

>     Description intent of your changes
>
>     [List of changes]
>
> 	  Signed-off-by: Your Name your@email.com

For example:

>     Add support of new platform
>
>     * Adding Dockerfile.<platform name>.server
>     * Fixing pytest args
>     * Adding platform specific testcases
>
>       Signed-off-by: user@dev.null


* Each developer should fork this repository and [add the team as a Contributor](https://help.github.com/articles/adding-collaborators-to-a-personal-repository)
* Push your changes to your private fork and do "pull-request" to this repository
* Use a pull request to do code review
* Use issues to keep track of what is going on

