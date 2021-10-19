
// Uploading duckcreek artifacts to nexus with specified paras like package_name to nexus URL & repos passed in this param 
def uploadArtifacts(artifact_id,artifact_version,package_name,package_type,nexus_URL,nexus_version,nexus_protocol,nexus_repository,nexus_groupID,nexus_credential)
{
	echo "Started uploading artifacts to Nexus repository"
	echo " upload file name : ${package_name} :"
	nexusArtifactUploader artifacts: [[artifactId: "${artifact_id}", file: "${package_name}", type: "${package_type}"]], credentialsId: "${nexus_credential}", groupId: "${nexus_groupID}", nexusUrl: "${nexus_URL}", nexusVersion: "${nexus_version}", protocol: "${nexus_protocol}", repository: "${nexus_repository}", version: "${artifact_version}"
	echo "Completed uploading artifacts to Nexus repository"
}