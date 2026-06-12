package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

public class CSVRecord_7_4Test {

    @Test
    public void testIterator_withValues() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = record.iterator();
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
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = record.iterator();
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_singleValue() throws Exception {
        String[] values = {"singleValue"};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = record.iterator();
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("singleValue", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_withNullValues() throws Exception {
        String[] values = {null, "value2", null};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = record.iterator();
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
        String[] values = {"", "value", " "};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = record.iterator();
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals(" ", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_specialCharacters() throws Exception {
        String[] values = {"value1", "value@2", "value#3"};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord record = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = record.iterator();
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value1", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value@2", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value#3", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }
}