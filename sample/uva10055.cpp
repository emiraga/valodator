/*
 * Solution for problem 10055 from UVa online judge
 */
#include <iostream>
using namespace std;

int main()
{
	long long a,b;
	while(cin >> a >> b)
	{
		if(a>b)
			cout << a-b << endl;
		else
			cout << b-a << endl;
	}
	return 0;
}

