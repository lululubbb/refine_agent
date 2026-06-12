package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_10_1Test {

    @Test
    public void testGetRecordNumber_normalCase() throws Exception {
        long expectedRecordNumber = 5L;
        CSVRecord csvRecord = createCSVRecord(expectedRecordNumber);

        long actualRecordNumber = csvRecord.getRecordNumber();

        Assertions.assertEquals(expectedRecordNumber, actualRecordNumber);
    }

    @Test
    public void testGetRecordNumber_zeroRecordNumber() throws Exception {
        long expectedRecordNumber = 0L;
        CSVRecord csvRecord = createCSVRecord(expectedRecordNumber);

        long actualRecordNumber = csvRecord.getRecordNumber();

        Assertions.assertEquals(expectedRecordNumber, actualRecordNumber);
    }

    @Test
    public void testGetRecordNumber_negativeRecordNumber() throws Exception {
        long expectedRecordNumber = -1L;
        CSVRecord csvRecord = createCSVRecord(expectedRecordNumber);

        long actualRecordNumber = csvRecord.getRecordNumber();

        Assertions.assertEquals(expectedRecordNumber, actualRecordNumber);
    }

    @Test
    public void testGet_validIndex() throws Exception {
        String[] values = new String[] {"value1", "value2", "value3"};
        CSVRecord csvRecord = createCSVRecord(1L, values);

        String actualValue = csvRecord.get(1);
        Assertions.assertEquals("value2", actualValue);
    }

    @Test
    public void testGetComment() throws Exception {
        String comment = "This is a comment";
        CSVRecord csvRecord = createCSVRecord(1L, new String[]{}, comment);

        String actualComment = csvRecord.getComment();
        Assertions.assertEquals(comment, actualComment);
    }

    @Test
    public void testIsConsistent() throws Exception {
        CSVRecord csvRecord = createCSVRecord(1L, new String[]{});

        boolean actualConsistency = csvRecord.isConsistent();
        Assertions.assertTrue(actualConsistency);
    }

    @Test
    public void testIsMapped() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("name", 0);
        CSVRecord csvRecord = createCSVRecord(1L, new String[]{"value"}, mapping);

        boolean actualMapped = csvRecord.isMapped("name");
        Assertions.assertTrue(actualMapped);
    }

    @Test
    public void testIsSet() throws Exception {
        String[] values = new String[] {"value1", "value2"};
        CSVRecord csvRecord = createCSVRecord(1L, values);

        boolean actualSet = csvRecord.isSet(1);
        Assertions.assertTrue(actualSet);
    }

    @Test
    public void testIterator() throws Exception {
        String[] values = new String[] {"value1", "value2"};
        CSVRecord csvRecord = createCSVRecord(1L, values);

        Iterator<String> iterator = csvRecord.iterator();
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value1", iterator.next());
    }

    @Test
    public void testSize() throws Exception {
        String[] values = new String[] {"value1", "value2", "value3"};
        CSVRecord csvRecord = createCSVRecord(1L, values);

        int actualSize = csvRecord.size();
        Assertions.assertEquals(3, actualSize);
    }

    @Test
    public void testToString() throws Exception {
        String[] values = new String[] {"value1", "value2"};
        CSVRecord csvRecord = createCSVRecord(1L, values);

        String actualString = csvRecord.toString();
        Assertions.assertEquals(Arrays.toString(values), actualString);
    }

    private CSVRecord createCSVRecord(long recordNumber) throws Exception {
        return createCSVRecord(recordNumber, new String[]{}, null);
    }

    private CSVRecord createCSVRecord(long recordNumber, String[] values) throws Exception {
        return createCSVRecord(recordNumber, values, null);
    }

    private CSVRecord createCSVRecord(long recordNumber, String[] values, String comment) throws Exception {
        Map<String, Integer> mapping = new HashMap<>();

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, comment, recordNumber);
    }
}