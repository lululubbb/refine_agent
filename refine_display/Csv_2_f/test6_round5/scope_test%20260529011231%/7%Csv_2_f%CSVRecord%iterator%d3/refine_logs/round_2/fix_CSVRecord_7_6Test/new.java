package org.apache.commons.csv;

import java.util.Arrays;
import java.io.Serializable;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_7_6Test {

    @Test
    public void testIterator_normalCase() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value1", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value3", iterator.next());
        Assertions.assertFalse(iterator.hasNext());

        // Additional check: iterator should return exactly the array elements in order
        String[] iteratedValues = new String[3];
        iterator = csvRecord.iterator();
        int i = 0;
        while (iterator.hasNext()) {
            iteratedValues[i++] = iterator.next();
        }
        Assertions.assertArrayEquals(values, iteratedValues);
    }

    @Test
    public void testIterator_emptyArray() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertFalse(iterator.hasNext());

        // Additional check: iterator should produce no elements
        int count = 0;
        while (iterator.hasNext()) {
            iterator.next();
            count++;
        }
        Assertions.assertEquals(0, count);
    }

    @Test
    public void testIterator_singleElement() throws Exception {
        String[] values = {"singleValue"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("singleValue", iterator.next());
        Assertions.assertFalse(iterator.hasNext());

        // Additional check: iterator should produce exactly one element matching the single value
        iterator = csvRecord.iterator();
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("singleValue", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
        
        // Check the size of the CSVRecord
        Assertions.assertEquals(1, csvRecord.size());
    }
}