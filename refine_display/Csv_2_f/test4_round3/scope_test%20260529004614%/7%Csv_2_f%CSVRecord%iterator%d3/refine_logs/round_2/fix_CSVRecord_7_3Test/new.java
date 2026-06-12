package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

public class CSVRecord_7_3Test {

    @Test
    public void testIterator_normalCase() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1L);

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
    public void testIterator_emptyValues() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1L);

        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_singleValue() throws Exception {
        String[] values = {"singleValue"};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1L);

        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("singleValue", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_withNullValues() throws Exception {
        String[] values = {null, "value2", null};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1L);

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
    public void testIterator_boundaryValues() throws Exception {
        String[] values = {"", "value2", "value3"};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1L);

        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value3", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }
}