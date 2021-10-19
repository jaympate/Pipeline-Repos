
// Unit Testing with dotnet framework utility for specified project 
def unitTestApplication(WSUnitTestProj)
{
	echo 'Starting unit test execution'
	//bat "NuGet restore ${APIUnitTestProj}"
	bat "dotnet test ${WSUnitTestProj} /p:Configuration=Release"
	echo 'Completed unit test execution'
}
