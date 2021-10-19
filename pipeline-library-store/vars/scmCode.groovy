
// check out code from git repo with specific branch using giving credential 
def gitCheckOut(repo_url,repo_branch,repo_credential){
	echo "Started to checkout branch - $repo_branch from git repository url - $repo_url with Credential=$repo_credential "
	git branch: "$repo_branch", changelog: false, credentialsId: "$repo_credential", url: "$repo_url"
	echo 'Completed checkout from Git'
}

// check out only specific folder from git repo with specified branch using giving credential 
def gitCheckOutFolder(repo_url,repo_branch,repo_credential,specific_folder){
	echo "Started checkout : branch - $repo_branch from git repository url - $repo_url of specific folder $specific_folder "
	checkout([$class: 'GitSCM', branches: [[name: "$repo_branch"]], doGenerateSubmoduleConfigurations: false, extensions: [[$class: 'SparseCheckoutPaths', sparseCheckoutPaths: [[path: "$specific_folder"]]]], submoduleCfg: [], userRemoteConfigs: [[credentialsId: "$repo_credential", url: "$repo_url"]]])
	echo "Completed checkout of specific folder $specific_folder "
}

// tagging at git repo with package 
def enableGitTagging(git_tag_credential){
	echo "Enable Git Tagging"
	withCredentials([usernamePassword(credentialsId: "$git_tag_credential", passwordVariable: 'password', usernameVariable: 'username')])
	{
		bat'''
			if "%release%"=="build" OR if "%release%"=="build_deploy"(
			setlocal ENABLEDELAYEDEXPANSION
			set word=com/api/v3/repos/
			set word1=/releases
			set str=%repo_host%
			set str=%str:com/=!word!%
			set str1=%str:.git=!word1!%
			curl -v -u %username%:%password% \
			--header "Accept:application/vnd.github.manifold-preview" \
			--data "{\\"tag_name\\": \\"%version%.%BUILD_NUMBER%\\", \\"target_commitish\\": \\"%branch%\\"}" \
			%str1% -X POST
			)
		'''
	}
}