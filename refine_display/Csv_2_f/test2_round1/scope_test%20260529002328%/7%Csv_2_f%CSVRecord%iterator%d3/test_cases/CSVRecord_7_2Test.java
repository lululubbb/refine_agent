package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

public class CSVRecord_7_2Test {

    @Test
    public void testIterator_withValues() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 0);

        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value1", iterator.next());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertEquals("value3", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_withEmptyValues() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 0);

        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_withNullValues() throws Exception {
        String[] values = null;
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 0);

        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_withSingleValue() throws Exception {
        String[] values = {"singleValue"};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 0);

        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("singleValue", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_withMultipleSameValues() throws Exception {
        String[] values = {"duplicate", "duplicate", "duplicate"};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 0);

        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("duplicate", iterator.next());
        Assertions.assertEquals("duplicate", iterator.next());
        Assertions.assertEquals("duplicate", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_withBoundaryValue() throws Exception {
        String[] values = {"", "value"};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 0);

        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("", iterator.next());
        Assertions.assertEquals("value", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }
}