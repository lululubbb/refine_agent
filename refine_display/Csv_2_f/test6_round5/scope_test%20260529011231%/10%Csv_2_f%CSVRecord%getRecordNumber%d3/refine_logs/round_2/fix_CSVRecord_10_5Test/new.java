package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_10_5Test {

    @Test
    public void testgetRecordNumber_normalCase() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        String comment = "This is a comment";
        long recordNumber = 5;

        CSVRecord csvRecord = createCSVRecord(values, mapping, comment, recordNumber);

        // Act
        long result = csvRecord.getRecordNumber();

        // Assert
        Assertions.assertEquals(recordNumber, result);
    }

    @Test
    public void testgetRecordNumber_zeroRecordNumber() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "This is a comment";
        long recordNumber = 0;

        CSVRecord csvRecord = createCSVRecord(values, mapping, comment, recordNumber);

        // Act
        long result = csvRecord.getRecordNumber();

        // Assert
        Assertions.assertEquals(recordNumber, result);
    }

    @Test
    public void testgetRecordNumber_negativeRecordNumber() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "This is a comment";
        long recordNumber = -1;

        CSVRecord csvRecord = createCSVRecord(values, mapping, comment, recordNumber);

        // Act
        long result = csvRecord.getRecordNumber();

        // Assert
        Assertions.assertEquals(recordNumber, result);
    }

    @Test
    public void testgetRecordNumber_boundaryValue() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "Boundary test";
        long recordNumber = Long.MAX_VALUE;

        CSVRecord csvRecord = createCSVRecord(values, mapping, comment, recordNumber);

        // Act
        long result = csvRecord.getRecordNumber();

        // Assert
        Assertions.assertEquals(recordNumber, result);
    }

    @Test
    public void testgetRecordNumber_exceptionThrowing() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "This is a comment";
        long recordNumber = -2; // Assuming negative values are invalid

        // Act & Assert
        Assertions.assertThrows(IllegalArgumentException.class, () -> {
            createCSVRecord(values, mapping, comment, recordNumber);
        });
    }

    private CSVRecord createCSVRecord(String[] values, Map<String, Integer> mapping, String comment, long recordNumber) throws NoSuchMethodException, IllegalAccessException, InvocationTargetException, InstantiationException {
        if (recordNumber < 0) {
            throw new IllegalArgumentException("Record number cannot be negative");
        }
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, comment, recordNumber);
    }
}