package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

public class CSVRecord_7_1Test {

    @Test
    public void testIterator_normalCase() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = csvRecord.iterator();
        
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value1", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value3", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_emptyArray() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_singleValue() throws Exception {
        String[] values = {"singleValue"};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("singleValue", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_withNullValues() throws Exception {
        String[] values = {null, "value2", null};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertNull(iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertNull(iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_boundaryCase() throws Exception {
        String[] values = {"boundary1", "boundary2"};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("boundary1", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("boundary2", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_largeArray() throws Exception {
        String[] values = new String[1000];
        Arrays.fill(values, "value");
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = csvRecord.iterator();

        for (int i = 0; i < 1000; i++) {
            Assertions.assertTrue(iterator.hasNext());
            Assertions.assertEquals("value", iterator.next());
        }
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_boundaryValues() throws Exception {
        String[] values = {"first", "second", "third", "fourth", "fifth"};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("first", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("second", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("third", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("fourth", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("fifth", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }
}