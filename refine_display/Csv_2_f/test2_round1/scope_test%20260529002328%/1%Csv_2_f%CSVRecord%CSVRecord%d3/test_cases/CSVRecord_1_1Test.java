package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.Map;

public class CSVRecord_1_1Test {

    @Test
    public void testCSVRecord_withValidParameters() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        String comment = "This is a comment";
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);

        Assertions.assertEquals("value1", record.get(0));
        Assertions.assertEquals("value2", record.get(1));
        Assertions.assertEquals("value3", record.get(2));
        Assertions.assertEquals(comment, record.getComment());
        Assertions.assertEquals(recordNumber, record.getRecordNumber());
        Assertions.assertEquals(3, record.size());
    }

    @Test
    public void testCSVRecord_withNullValues() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "This is a comment";
        long recordNumber = 1;

        CSVRecord record = new CSVRecord(null, mapping, comment, recordNumber);

        Assertions.assertArrayEquals(new String[0], record.values());
        Assertions.assertEquals(comment, record.getComment());
        Assertions.assertEquals(recordNumber, record.getRecordNumber());
        Assertions.assertEquals(0, record.size());
    }

    @Test
    public void testCSVRecord_withEmptyMapping() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>(); // Empty mapping
        String comment = "Another comment";
        long recordNumber = 2;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);

        Assertions.assertFalse(record.isConsistent()); // Expect false because mapping is empty
        Assertions.assertFalse(record.isMapped("column1"));
        Assertions.assertFalse(record.isSet("column1"));
    }

    @Test
    public void testCSVRecord_withComment() throws Exception {
        String[] values = {"value1"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "This is a comment";
        long recordNumber = 3;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);

        Assertions.assertEquals(comment, record.getComment());
        Assertions.assertEquals(1, record.size());
    }

    @Test
    public void testCSVRecord_iterator() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "Comment";
        long recordNumber = 4;

        CSVRecord record = new CSVRecord(values, mapping, comment, recordNumber);
        Iterator<String> iterator = record.iterator();

        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value1", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }
}