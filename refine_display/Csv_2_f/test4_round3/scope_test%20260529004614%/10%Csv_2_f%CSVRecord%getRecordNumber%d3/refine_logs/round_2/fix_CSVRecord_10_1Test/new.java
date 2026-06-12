package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_10_1Test {

    @Test
    public void testgetRecordNumber_normalCase() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "Test comment";
        long recordNumber = 5L;

        CSVRecord csvRecord = createCSVRecord(values, mapping, comment, recordNumber);
        long result = csvRecord.getRecordNumber();

        Assertions.assertEquals(recordNumber, result);
        Assertions.assertEquals(5L, result); // Strengthened assertion
    }

    @Test
    public void testgetRecordNumber_zeroRecordNumber() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "Test comment";
        long recordNumber = 0L;

        CSVRecord csvRecord = createCSVRecord(values, mapping, comment, recordNumber);
        long result = csvRecord.getRecordNumber();

        Assertions.assertEquals(recordNumber, result);
        Assertions.assertEquals(0L, result); // Strengthened assertion
    }

    @Test
    public void testgetRecordNumber_negativeRecordNumber() throws Exception {
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "Test comment";
        long recordNumber = -10L;

        CSVRecord csvRecord = createCSVRecord(values, mapping, comment, recordNumber);
        long result = csvRecord.getRecordNumber();

        Assertions.assertEquals(recordNumber, result);
        Assertions.assertEquals(-10L, result); // Strengthened assertion
    }

    private CSVRecord createCSVRecord(String[] values, Map<String, Integer> mapping, String comment, long recordNumber) throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance((Object) values, mapping, comment, recordNumber);
    }
}