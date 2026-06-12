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
        String comment = "Test comment";
        long recordNumber = 1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertEquals("value1", iterator.next());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertEquals("value3", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_emptyArray() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        String comment = "Test comment";
        long recordNumber = 1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_singleElement() throws Exception {
        String[] values = {"singleValue"};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        String comment = "Test comment";
        long recordNumber = 1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertEquals("singleValue", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_nullValues() throws Exception {
        String[] values = {null, "value2", "value3"};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        String comment = "Test comment";
        long recordNumber = 1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertNull(iterator.next());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertEquals("value3", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testIterator_emptyString() throws Exception {
        String[] values = {"", "value2", "value3"};
        Map<String, Integer> mapping = Mockito.mock(Map.class);
        String comment = "Test comment";
        long recordNumber = 1L;

        CSVRecord csvRecord = new CSVRecord(values, mapping, comment, recordNumber);
        Iterator<String> iterator = csvRecord.iterator();

        Assertions.assertEquals("", iterator.next());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertEquals("value3", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }
}