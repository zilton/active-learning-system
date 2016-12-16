/*
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */
package weka.classifiers.rules;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.collections.primitives.ArrayIntList;
import org.apache.commons.collections.primitives.IntIterator;

/**
 * A simple way to store and lookup instances that have a given combination of
 * features. For each feature on training set, we store an entry on a
 * {@link Map}. <br/>
 * This entry is a set of integers. Each integer is the index of an {@link LACInstance}
 * that contains those features.
 * 
 * @author Gesse Dafe (Java implementation)
 * @author Adriano Veloso (algorithm and original C++ implementation)
 */
public class LACFeatureOccurrences implements Serializable
{
	private static final long serialVersionUID = -3942414672290094335L;
	private Map<Integer, ArrayIntList> map = new HashMap<Integer, ArrayIntList>();
	private final LACLRU<List<Integer>, ArrayIntList> cache = new LACLRU<List<Integer>, ArrayIntList>(10000);

	/**
	 * Creates the map of features for all entries in {@link LACInstances}.
	 * 
	 * @param instances
	 */
	void createMap(LACInstances instances)
	{
		for (int currentPosition = 0; currentPosition < instances.length(); currentPosition++)
		{
			LACInstance currentInstance = instances.getInstance(currentPosition);
			List<Integer> indexedFeatures = currentInstance.getIndexedFeatures();
			int size = indexedFeatures.size();
			for (int currentFeaturePosition = 0; currentFeaturePosition < size; currentFeaturePosition++)
			{
				int currentIndexedFeature = indexedFeatures.get(currentFeaturePosition);
				ArrayIntList instancesContainingFeature = map.get(currentIndexedFeature);
				if (instancesContainingFeature == null)
				{
					instancesContainingFeature = new ArrayIntList();
					map.put(currentIndexedFeature, instancesContainingFeature);
				}
				instancesContainingFeature.add(currentPosition);
			}
		}
	}

	@Override
	public String toString()
	{
		return map.toString();
	}

	/**
	 * Gets all instances which contain all given features
	 * 
	 * @param featuresIndexes
	 * @return
	 */
	public List<Integer> instancesWithFeatures(List<Integer> featuresIndexes)
	{
		ArrayIntList instances = cache.get(featuresIndexes);
		List<Integer> result = new ArrayList<Integer>();
		
		if (instances == null)
		{
			if (featuresIndexes.size() == 1)
			{
				instances = map.get(featuresIndexes.get(0));
				if (instances != null){
					for(IntIterator iter = instances.iterator(); iter.hasNext(); ) {
						result.add(iter.next());
					}
				}
			}
			else
			{
				instances = new ArrayIntList();

				Integer feature = featuresIndexes.get(0);
				ArrayIntList instancesForCurrFeat = map.get(feature);

				if (instancesForCurrFeat == null || instancesForCurrFeat.size() == 0)
				{
					return Collections.emptyList();
				}
				else
				{
					List<Integer> otherfeatures = new ArrayList<Integer>();
					otherfeatures.addAll(featuresIndexes);
					otherfeatures.remove(0);

					instances.addAll(instancesForCurrFeat);
					List<Integer> rest = instancesWithFeatures(otherfeatures);
					if(rest != null)
					{
						List<Integer> instancesAsList = new ArrayList<Integer>();
						for(IntIterator iter = instances.iterator(); iter.hasNext(); ) {
							instancesAsList.add(iter.next());
						}
						result = calculateIntersection(instancesAsList, rest);
						///cache.put(featuresIndexes, instances);
					}
					else
					{
						///cache.put(featuresIndexes, new ArrayIntList());
					}
				}
			}
		}

		return result;
	}

	/**
	 * Calculates the intersection one two lists sorted in ascending order. Both
	 * lists must not have duplicated elements.
	 * 
	 * @param oneList
	 * @param otherList
	 */
	private List<Integer> calculateIntersection(List<Integer> oneList, List<Integer> otherList)
	{
		List<Integer> intersection = new ArrayList<Integer>();

		int oneIndex = 0;
		int oneSize = oneList.size();

		int otherIndex = 0;
		int otherSize = otherList.size();

		while (oneIndex < oneSize && otherIndex < otherSize)
		{
			int oneElem = oneList.get(oneIndex);
			int otherElem = otherList.get(otherIndex);

			if (oneElem == otherElem)
			{
				intersection.add(oneElem);
				oneIndex++;
				otherIndex++;
			}
			else if (oneElem < otherElem)
			{
				oneIndex = linearSearch(otherElem, oneIndex, oneSize - 1, oneList);
			}
			else
			{
				otherIndex = linearSearch(oneElem, otherIndex, otherSize - 1, otherList);
			}
		}

		return intersection;
	}

	/**
	 * Executes a linear search for the given element on the list
	 * 
	 * @param elem
	 * @param start
	 * @param end
	 * @param list
	 * @return the index of the element if it exists. Otherwise, returns the
	 *         index of the first greater element.
	 */
	private int linearSearch(int elem, int start, int end, List<Integer> list)
	{
		int last = list.get(end);

		if (elem > last)
		{
			return end + 1;
		}
		else
		{
			int size = list.size();
			while (start < size && list.get(start) < elem)
			{
				start++;
			}
			return start;
		}
	}
}
