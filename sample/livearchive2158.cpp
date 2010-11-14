/*
 * Solution to problem 2158 from livearchive
 */
#include <iostream>
using namespace std;

int main()
{
	int t;
	cin >> t;
	for(int i=0; i<t; i++)
	{
		int n, k = 5, res = 0;
		cin >> n;
		while(n >= k)
		{
			res += n/k;
			k *= 5;
		}
		cout << res << endl;
	}
	return 0;
}

