package org.apache.commons.csv;

import java.util.Arrays;
import java.util.Iterator;
import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_2_1Test {

    @Test
    public void testGet_validIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        String result = invokeGetMethod(record, 1);
        Assertions.assertEquals("value2", result);
    }

    @Test
    public void testGet_zeroIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        String result = invokeGetMethod(record, 0);
        Assertions.assertEquals("value1", result);
    }

    @Test
    public void testGet_lastIndex() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        String result = invokeGetMethod(record, 2);
        Assertions.assertEquals("value3", result);
    }

    @Test
    public void testGet_invalidIndex_negative() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            invokeGetMethod(record, -1);
        });
    }

    @Test
    public void testGet_invalidIndex_outOfBounds() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        Assertions.assertThrows(ArrayIndexOutOfBoundsException.class, () -> {
            invokeGetMethod(record, 3);
        });
    }

    private String invokeGetMethod(CSVRecord record, int index) throws Exception {
        try {
            return record.get(index);
        } catch (ArrayIndexOutOfBoundsException e) {
            throw e; // rethrow the exception to be caught in the test
        }
    }
}